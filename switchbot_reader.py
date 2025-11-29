#!/usr/bin/env python3
"""
SwitchBot温湿度計からBLEアドバタイズメントデータで温度・湿度を取得するプログラム
1秒ごとにデータを読み取り表示する
"""

import argparse
import asyncio
import time
import requests

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

"""
influxdb3用定数
"""
INFLUXDB3_URL = ""
INFLUXDB3_TOKEN = ""
INFLUXDB3_DATABASE = ""

"""
BLEスキャン用定数
"""
SCAN_DURATION = 10.0  # スキャン時間（秒）

"""
デフォルトデバイス設定
"""
DEFAULT_DEVICES = {
    "xx:xx:xx:xx:xx:xx": {"location": "bedroom", "device_type": "meter"},
    "xx:xx:xx:xx:xx:xx": {"location": "workroom", "device_type": "co2"},
}


class SwitchBotDevice:
    """SwitchBotデバイスの定義と管理"""

    def __init__(self, mac_address, location, device_type="meter"):
        self.mac_address = mac_address.lower()
        self.location = location
        self.device_type = device_type

    def __repr__(self):
        return (
            f"SwitchBotDevice({self.mac_address}, {self.location}, {self.device_type})"
        )

    def matches_address(self, address):
        """MACアドレスがマッチするかチェック"""
        return self.mac_address == address.lower()


class BLEAdvertisementScanner:
    """BLEアドバタイズメントスキャナー"""

    def __init__(self, devices, debug_mode=False, influxdb_config=None):
        self.devices = devices if isinstance(devices, list) else [devices]
        self.debug_mode = debug_mode
        self.influxdb_config = influxdb_config

        # デバイスのMACアドレスリストを作成
        self.target_addresses = [device.mac_address for device in self.devices]

    def get_device_by_address(self, address):
        """MACアドレスからデバイスを取得"""
        for device in self.devices:
            if device.matches_address(address):
                return device
        return None

    def parse_advertisement_data(self, advertisement_data):
        """アドバタイズメントデータから温度・湿度・CO2を解析"""
        try:
            temperature = None
            humidity = None
            battery_pct = None
            co2_ppm = None

            # manufacturer_data (Type: 0xFF) から温湿度解析
            if (
                hasattr(advertisement_data, "manufacturer_data")
                and advertisement_data.manufacturer_data
            ):
                for company_id, data in advertisement_data.manufacturer_data.items():
                    if self.debug_mode:
                        print(
                            f"Debug: Company ID: {hex(company_id)}, Data: {data.hex()}, Length: {len(data)}"
                        )

                    if len(data) >= 12:  # 12バイト必要
                        # バイトを表示
                        if self.debug_mode:
                            for i, byte in enumerate(data):
                                print(
                                    f"  Byte[{i}]: 0x{byte:02x} ({byte}) = 0b{byte:08b}"
                                )

                        # - 温度: 8バイト目下位4ビット(小数部) + 9バイト目下位7ビット(整数部) + 10バイト目上位1ビット(符号)
                        # - 湿度: 10バイト目下位7ビット
                        temp_decimal = (data[8] & 0x0F) * 0.1  # 8バイト目の下位4ビット
                        temp_integer = data[9] & 0x7F  # 9バイト目の下位7ビット
                        if len(data) == 12:
                            temp_sign = (
                                data[10] & 0x80
                            ) > 0  # 防水温湿度計は10バイト目の上位1ビット
                        elif len(data) == 16:
                            temp_sign = (
                                data[9] & 0x80
                            ) > 0  # CO2センサーは多分9バイト目の上位1ビット
                        temperature = temp_decimal + temp_integer
                        if not temp_sign:
                            temperature = -temperature
                        humidity = data[10] & 0x7F  # 10バイト目の下位7ビット

                        if len(data) == 16:
                            co2_ppm = data[13] * 256 + data[14]
                        if self.debug_mode:
                            print("  温度解析:")
                            print(
                                f"    8バイト目(0x{data[8]:02x}): 下位4ビット = {data[8] & 0x0F} -> 小数部 {temp_decimal}"
                            )
                            print(
                                f"    9バイト目(0x{data[9]:02x}): 下位7ビット = {data[9] & 0x7F} -> 整数部 {temp_integer}"
                            )
                            if len(data) == 12:
                                print(
                                    f"    10バイト目(0x{data[10]:02x}): 上位1ビット = {temp_sign} -> 符号 {'正' if temp_sign else '負'}"
                                )
                            elif len(data) == 16:
                                print(
                                    f"    9バイト目(0x{data[9]:02x}): 上位1ビット = {temp_sign} -> 符号 {'正' if temp_sign else '負'}"
                                )

                            print(f"  -> 温度: {temperature:.1f}°C")

                            print("  湿度解析:")
                            print(
                                f"    10バイト目(0x{data[10]:02x}): 下位7ビット = {data[10] & 0x7F}"
                            )
                            print(f"  -> 湿度: {humidity}%")

                            if len(data) == 16:
                                print("  CO2解析:")
                                print(
                                    f"    14バイト目(0x{data[13]:02x}): x256 = {data[13] * 256}"
                                )
                                print(f"    15バイト目(0x{data[14]:02x}): = {data[14]}")
                                print(f"  -> CO2: {co2_ppm}ppm")

            # service_data (Type: 0x16) からバッテリー解析
            if (
                hasattr(advertisement_data, "service_data")
                and advertisement_data.service_data
            ):
                for uuid, data in advertisement_data.service_data.items():
                    if self.debug_mode:
                        print(
                            f"Debug: Service UUID: {uuid}, Data: {data.hex()}, Length: {len(data)}"
                        )

                    if len(data) >= 3:
                        # バイトを表示
                        if self.debug_mode:
                            for i, byte in enumerate(data):
                                print(f"  Service Byte[{i}]: 0x{byte:02x} ({byte})")

                        # 下位1バイト（最後のバイト）がバッテリー残量
                        battery_pct = data[-1]  # 最後のバイト
                        if self.debug_mode:
                            print(f"  バッテリー: {battery_pct}%")

            if temperature is not None and humidity is not None:
                return temperature, humidity, battery_pct, co2_ppm

        except Exception as e:
            print(f"データ解析エラー: {e}")
            import traceback

            traceback.print_exc()

        return None, None, None, None

    def send_to_influxdb(
        self, device, temperature, humidity, battery_pct, co2_ppm=None
    ):
        """InfluxDB 3にデータを送信（直接APIコール）"""
        if not self.influxdb_config:
            return

        try:
            # Line Protocolフォーマットでデータを構築
            fields = [
                f"temperature={float(temperature)}",
                f"humidity={float(humidity)}",
            ]

            if battery_pct is not None:
                fields.append(f"battery_pct={float(battery_pct)}")

            if co2_ppm is not None:
                fields.append(f"co2_ppm={float(co2_ppm)}")

            tags = [
                f"location={device.location}",
                f"mac_address={device.mac_address}",
                f"device_type={device.device_type}",
            ]

            # Line Protocol形式の文字列を構築
            line_protocol = f"sensor,{','.join(tags)} {','.join(fields)}"

            # InfluxDB API v3エンドポイント
            url = f"{self.influxdb_config['url'].rstrip('/')}/api/v3/write_lp"

            headers = {
                "Authorization": f"Bearer {self.influxdb_config['token']}",
                "Content-Type": "text/plain; charset=utf-8",
            }

            params = {"db": self.influxdb_config["database"], "precision": "second"}

            # HTTPリクエストでデータ送信
            response = requests.post(
                url, data=line_protocol, headers=headers, params=params, timeout=10
            )

            if response.status_code == 204:
                if self.debug_mode:
                    print(f"InfluxDB 3にデータを送信しました: {device.mac_address}")
            else:
                print(
                    f"InfluxDB送信エラー: HTTP {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            print(f"InfluxDB HTTP送信エラー: {e}")
        except Exception as e:
            print(f"InfluxDB送信エラー: {e}")

    async def scan_once(self):
        """1回だけBLEスキャンを実行してデータを読み取る"""
        found_devices = {}

        def detection_callback(
            device: BLEDevice, advertisement_data: AdvertisementData
        ):
            # 登録されたデバイスのみ処理
            target_device = self.get_device_by_address(device.address)
            if not target_device:
                return

            result = self.parse_advertisement_data(advertisement_data)
            if result and len(result) == 4:
                temp, humidity, battery, co2_ppm = result
                if temp is not None and humidity is not None:
                    # 最新のデータで上書き（同じデバイスから複数回受信した場合）
                    found_devices[device.address] = {
                        "device": target_device,
                        "ble_device": device,
                        "temp": temp,
                        "humidity": humidity,
                        "battery": battery,
                        "co2_ppm": co2_ppm,
                    }
            elif self.debug_mode:
                # デバッグ用：生データを表示
                print(f"データなし: {device.name} ({device.address})")
                if (
                    hasattr(advertisement_data, "manufacturer_data")
                    and advertisement_data.manufacturer_data
                ):
                    for (
                        company_id,
                        data,
                    ) in advertisement_data.manufacturer_data.items():
                        print(f"  Manufacturer {hex(company_id)}: {data.hex()}")
                if (
                    hasattr(advertisement_data, "service_data")
                    and advertisement_data.service_data
                ):
                    for uuid, data in advertisement_data.service_data.items():
                        print(f"  Service {uuid}: {data.hex()}")

        # スキャンを開始
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()

        # スキャン時間（短時間でデータを収集）
        await asyncio.sleep(SCAN_DURATION)

        # スキャンを停止
        await scanner.stop()

        # 見つかったデバイスのデータを表示・送信
        for address, data in found_devices.items():
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            device_name = data["ble_device"].name or "SwitchBot"
            battery_info = (
                f", バッテリー: {data['battery']}%"
                if data["battery"] is not None
                else ""
            )
            co2_info = (
                f", CO2: {data['co2_ppm']}ppm"
                if data["co2_ppm"] is not None
                else ""
            )
            print(
                f"[{timestamp}] {device_name} ({address}) @ {data['device'].location} - 温度: {data['temp']:.1f}°C, 湿度: {data['humidity']}%{battery_info}{co2_info}"
            )

            # InfluxDBにデータを送信
            self.send_to_influxdb(
                data["device"],
                data["temp"],
                data["humidity"],
                data["battery"],
                data["co2_ppm"],
            )

        return found_devices


async def main():
    parser = argparse.ArgumentParser(description="SwitchBot BLE読み取りプログラム")
    parser.add_argument("--debug", action="store_true", help="デバッグ情報を表示")
    parser.add_argument(
        "--mac", action="append", help="監視するMACアドレス（複数指定可能）"
    )
    parser.add_argument(
        "--device-type",
        choices=["meter", "co2"],
        default="meter",
        help="デバイス種別 (meter: 防水温湿度計, co2: CO2センサー)",
    )

    # InfluxDB 3関連引数
    parser.add_argument(
        "--influxdb",
        action="store_true",
        help="InfluxDB 3への書き込みON/OFFフラグ(default=off)",
        default=False,
    )
    parser.add_argument(
        "--influxdb-url", help="InfluxDB 3 URL (例: http://localhost:8086)"
    )
    parser.add_argument("--influxdb-token", help="InfluxDB 3 APIトークン")
    parser.add_argument(
        "--influxdb-database",
        default="switchbot_meter",
        help="InfluxDB 3データベース名 (デフォルト: switchbot_meter)",
    )
    parser.add_argument("--location", help="デバイスの場所（タグ用）")

    args = parser.parse_args()

    # デバイス設定の処理
    devices = []
    if args.mac:
        # CLI引数で指定されたMACアドレス
        for mac in args.mac:
            devices.append(
                SwitchBotDevice(
                    mac_address=mac,
                    location=args.location or "unknown",
                    device_type=args.device_type,
                )
            )
    else:
        # デフォルトデバイスを使用
        for mac, config in DEFAULT_DEVICES.items():
            devices.append(
                SwitchBotDevice(
                    mac_address=mac,
                    location=config["location"],
                    device_type=config["device_type"],
                )
            )

    # InfluxDB 3設定
    influxdb_config = None
    if args.influxdb:
        if args.influxdb_url and args.influxdb_token:
            influxdb_config = {
                "url": args.influxdb_url,
                "token": args.influxdb_token,
                "database": args.influxdb_database,
            }
        else:
            influxdb_config = {
                "url": INFLUXDB3_URL,
                "token": INFLUXDB3_TOKEN,
                "database": INFLUXDB3_DATABASE,
            }

    # スキャナーを作成
    scanner = BLEAdvertisementScanner(
        devices=devices,
        debug_mode=args.debug,
        influxdb_config=influxdb_config,
    )

    print("SwitchBot BLE読み取りプログラム")
    print("対象デバイス:")
    for device in devices:
        print(f"  {device.mac_address} ({device.device_type} @ {device.location})")
    print("モード: ワンショット")
    if args.influxdb:
        print(f"InfluxDB 3送信: ON (URL: {influxdb_config['url']})")
        print(f"データベース: {influxdb_config['database']}")
    if args.debug:
        print("デバッグモード: ON")
    print("-" * 40)

    # アドバタイズメントデータから読み取り
    await scanner.scan_once()


if __name__ == "__main__":
    # 必要なパッケージの確認
    try:
        import bleak

        print("bleak パッケージが利用可能です")
    except ImportError:
        print("エラー: bleakパッケージがインストールされていません")
        print("インストール方法: pip install bleak")
        exit(1)

    # 権限の確認メッセージ
    print("注意: このプログラムの実行にはBluetooth権限が必要です")
    print("sudoで実行するか、ユーザーをbluetoothグループに追加してください")
    print("")

    # プログラム実行
    asyncio.run(main())
