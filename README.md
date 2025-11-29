# SwitchBot BLE Reader

SwitchBotデバイス（防水温湿度計・CO2センサー）からBLE（Bluetooth Low Energy）アドバタイズメントデータで温度・湿度・バッテリー情報を読み取るPythonプログラムです。

## 特徴

- 🌡️ **リアルタイム監視**: 1秒ごとの温度・湿度データ取得
- 🔋 **バッテリー情報**: デバイスのバッテリー残量も表示
- 📡 **接続不要**: BLEアドバタイズメントデータから読み取り（デバイスへの負荷なし）
- 🎯 **高精度**: 温度0.1度単位、湿度1%単位で取得
- 📱 **複数デバイス対応**: 複数のMACアドレス指定が可能
- 🔧 **デバイス種別対応**: 防水温湿度計とCO2センサーに対応
- 🐛 **デバッグモード**: 詳細なデバッグ情報表示機能
- ⚡ **軽量**: uvを使った高速なパッケージ管理

## 必要な環境

- **Python 3.11以上**
- **Linux または macOS**（Bluetoothスタック対応）
- **SwitchBotデバイス**（防水温湿度計またはCO2センサー）

## セットアップ

### 1. uvのインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. プロジェクトのクローン/ダウンロード

```bash
# プロジェクトディレクトリに移動
cd switchbot-ble-reader
```

### 3. 依存関係のインストール

```bash
uv sync
```

### 4. Bluetooth権限の設定

#### Linux の場合
```bash
# ユーザーをbluetoothグループに追加
sudo usermod -a -G bluetooth $USER

# 再ログインまたは再起動が必要
```

#### macOS の場合
- **システム環境設定** → **セキュリティとプライバシー** → **プライバシー** → **Bluetooth**
- TerminalまたはITerm2にBluetooth権限を付与

## 使用方法

### コマンドライン引数

```bash
# ヘルプ表示
uv run python switchbot_reader.py --help
```

**利用可能な引数:**
- `--mac`: 監視するMACアドレス（複数指定可能）
- `--device-type`: デバイス種別（`meter`: 防水温湿度計, `co2`: CO2センサー）
- `--debug`: デバッグ情報を表示
- `--location`: デバイスの場所（InfluxDB 3タグ用）
- `--influxdb-url`: InfluxDB 3 URL
- `--influxdb-token`: InfluxDB 3 APIトークン
- `--influxdb-database`: InfluxDB 3データベース名 (デフォルト: switchbot_meter)

### 基本的な実行

```bash
# デフォルト設定で実行（防水温湿度計、デフォルトMACアドレス）
uv run python switchbot_reader.py

# 特定のMACアドレスを指定
uv run python switchbot_reader.py --mac AA:BB:CC:DD:EE:FF

# 複数のデバイスを監視
uv run python switchbot_reader.py --mac AA:BB:CC:DD:EE:FF --mac AA:BB:CC:DD:EE:F0

# CO2センサーを監視
uv run python switchbot_reader.py --device-type co2 --mac AA:BB:CC:DD:EE:FF

# デバッグモードで実行
uv run python switchbot_reader.py --debug --mac AA:BB:CC:DD:EE:FF
```

### InfluxDB 3連携

```bash
# InfluxDB 3にデータを送信
uv run python switchbot_reader.py \
  --mac AA:BB:CC:DD:EE:FF \
  --location "リビング" \
  --influxdb-url http://localhost:8086 \
  --influxdb-token your_token_here \
  --influxdb-database switchbot_meter

# 複数デバイスでInfluxDB 3連携
uv run python switchbot_reader.py \
  --mac AA:BB:CC:DD:EE:FF \
  --mac AA:BB:CC:DD:EE:FF \
  --location "家庭" \
  --interval 30 \
  --influxdb-url http://localhost:8086 \
  --influxdb-token your_token_here \
  --influxdb-database switchbot_meter

# CO2センサーでInfluxDB 3連携
uv run python switchbot_reader.py \
  --device-type co2 \
  --mac AA:BB:CC:DD:EE:FF \
  --location "寝室" \
  --influxdb-url http://localhost:8086 \
  --influxdb-token your_token_here \
  --influxdb-database switchbot_meter
```

### 実行例

#### 基本実行例

```
SwitchBot meter BLE読み取りプログラム
対象デバイス: AA:BB:CC:DD:EE:FF
インターバル: 1.0秒
Ctrl+Cで終了
----------------------------------------
[2025-06-16 22:45:30] SwitchBot (AA:BB:CC:DD:EE:FF) - 温度: 25.1°C, 湿度: 61%, バッテリー: 100%
[2025-06-16 22:45:31] SwitchBot (AA:BB:CC:DD:EE:FF) - 温度: 25.2°C, 湿度: 61%, バッテリー: 100%
```

#### InfluxDB 3連携実行例

```
SwitchBot meter BLE読み取りプログラム
対象デバイス: AA:BB:CC:DD:EE:FF
インターバル: 1.0秒
InfluxDB 3送信: ON (http://localhost:8086)
データベース: switchbot_meter
場所: リビング
Ctrl+Cで終了
----------------------------------------
[2025-06-16 22:45:30] SwitchBot (AA:BB:CC:DD:EE:FF) - 温度: 25.1°C, 湿度: 61%, バッテリー: 100%
[2025-06-16 22:45:31] SwitchBot (AA:BB:CC:DD:EE:FF) - 温度: 25.2°C, 湿度: 61%, バッテリー: 100%
```

## 開発

### コード品質ツール

このプロジェクトでは[Ruff](https://github.com/astral-sh/ruff)を使用してコードの品質管理を行っています。

```bash
# コードチェック + 自動修正
uv run ruff check --fix .

# フォーマット
uv run ruff format .

# 両方を一度に実行
uv run ruff check --fix . && uv run ruff format .
```

### プロジェクト構造

```
switchbot-ble-reader/
├── switchbot_reader.py    # メインプログラム
├── pyproject.toml         # プロジェクト設定
├── README.md             # このファイル
└── .venv/                # 仮想環境（uvが自動作成）
```

## 技術詳細

### データ形式

#### Manufacturer Data（Type: 0xFF）
- **温度**: 8バイト目下位4ビット（小数部）+ 9バイト目下位7ビット（整数部）+ 10バイト目上位1ビット（符号）
- **湿度**: 10バイト目下位7ビット

#### Service Data（Type: 0x16）
- **バッテリー**: 最下位バイト

### InfluxDB 3データスキーマ

**Database**: `switchbot_meter`
**Table**: `sensor`

**Tags**:
- `location`: デバイスの場所
- `device_type`: デバイス種別 (meter/co2)

**Fields**:
- `temp`: 温度 (°C)
- `hum`: 湿度 (%)
- `battery`: バッテリー残量 (%) - オプション
- `co2ppm`: CO2濃度 (ppm) - CO2センサーのみ

### 使用ライブラリ

- **[bleak](https://github.com/hbldh/bleak)**: クロスプラットフォームBLEライブラリ
- **[influxdb3-python](https://github.com/InfluxCommunity/influxdb3-python)**: InfluxDB 3クライアントライブラリ
- **asyncio**: 非同期処理
- **struct**: バイナリデータ解析

## トラブルシューティング

### デバイスが見つからない場合

1. **SwitchBot温湿度計の電源確認**
   - デバイスが動作していることを確認
   - 必要に応じて電池交換

2. **Bluetooth設定確認**
   ```bash
   # Bluetoothサービスの状態確認（Linux）
   sudo systemctl status bluetooth
   
   # Bluetoothデバイスの確認
   bluetoothctl devices
   ```

3. **距離の確認**
   - デバイスとの距離を近づける（1-2m以内推奨）

### 権限エラーが発生する場合

```bash
# sudo で実行
sudo uv run python switchbot_reader.py
```

### データが正しくない場合

デバッグモードを使用して、生のBLEデータを解析：

```bash
# デバッグモードで実行
uv run python switchbot_reader.py --debug --mac AA:BB:CC:DD:EE:FF
```

## ライセンス

MIT License

## 参考資料

- [SwitchBot API Documentation](https://github.com/OpenWonderLabs/SwitchBotAPI-BLE)
- [bleak Documentation](https://bleak.readthedocs.io/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

## 貢献

バグ報告や機能追加の提案は、GitHubのIssuesでお願いします。プルリクエストも歓迎します！

---

**注意**: このプログラムはSwitchBot防水温湿度計とCO2センサー専用です。他のSwitchBotデバイス（通常の温湿度計など）では異なるデータ形式を使用しているため、正しく動作しない可能性があります。
