# Default Test Naming Rules

This file defines the default mapping between test condition names and data identifiers across different SOC (State of Charge) levels.

## Format

Each line defines one sensor channel in the format:
```
ChannelCode: ComponentDescription(Unit)
```

- **ChannelCode ending with `_A`**: Current measurement (Amperes)
- **ChannelCode ending with `_V`**: Voltage measurement (Volts)

## Default Sensor Channels

FM_V: 前电驱系统直流母线端电压(V)
FM_A: 前电驱系统直流母线端电流(A)
RM_V: 后电驱系统直流母线端电压(V)
RM_A: 后电驱系统直流母线端电流(A)
DCC_V: 动力电池直流充电端电压(V)
DCC_A: 动力电池直流充电端电流(A)
ACC_V: OBC输出端电压(V)
ACC_A: OBC输出端电流(A)
PTC_V: PTC输入端电压(V)
PTC_A: PTC输入端电流(A)
ACCM_V: 压缩机输入端电压(V)
ACCM_A: 压缩机输入端电流(A)
LV_V: 12V电池及前端冷却模块风扇的低压电压(V)
LV_A: 12V电池及前端冷却模块风扇的低压电流(A)
FAN_A: 前端冷却模块风扇的低压电流(A)
BATT_V: 动力电池电压(V)
BATT_A: 动力电池电流(A)
Vehicle_Harness_Splitter_V: 车辆分线器端的电压(V)
Vehicle_Harness_Splitter_A: 车辆分线器端的电流(A)
IF_V: 电驱到智能前舱分线接头之间的电压(V)
IF_A: 电驱到智能前舱分线接头之间的电流(A)
fendianqi_V: 车辆分线器端的电压(V)
fendianqi_A: 车辆分线器端的电流(A)
yasuoji_A: 压缩机输入端电流(A)

## Notes

- **Channel codes must match component folder names exactly**
- **Sensor channel is determined by the FOLDER name, NOT the image filename**
- Unit is automatically determined by suffix: `_A` = Amperes, `_V` = Volts
- If you need different sensor configurations, create a custom sensor_naming_rules.md in your vehicle folder

## Important: Folder Name Determines Sensor Channel

**The folder name is the source of truth for the sensor channel.**

Example folder structure:
```
V0001_SLOPE/
├── FM_V/                    # Sensor channel = FM_V (from folder name)
│   ├── statistics.xlsx
│   └── 87_超车80-140_FM_V.png  # Channel in filename should match folder
├── LV_A/                    # Sensor channel = LV_A (from folder name)
│   ├── statistics.xlsx
│   └── 87_超车80-140_LV_A.png  # Channel in filename should match folder
```

- The processor uses the **folder name** as the sensor channel identifier
- Image filenames should end with `_{channel_code}` to allow condition matching
- If image filename channel doesn't match folder name, a warning will be issued
