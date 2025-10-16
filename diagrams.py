import re
import json
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import glob
import os

# === Einstellungen ===
ordner = "log"
dateimuster = "Offgrid*.log"

zeiten = []
soc = []
output_power = []

dateiliste = sorted(glob.glob(os.path.join(ordner, dateimuster)))

if not dateiliste:
    print(f"⚠️ Keine Dateien gefunden in: {os.path.abspath(ordner)}")
    exit()
else:
    print(f"📂 {len(dateiliste)} Dateien gefunden, lese ein...")

jetzt = datetime.now()
fehler_zeilen = 0

for dateiname in dateiliste:
    print(f"→ Lese {os.path.basename(dateiname)}")

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", dateiname)
    if date_match:
        datum = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
    else:
        datum = jetzt.date()

    with open(dateiname, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            zeit_match = re.match(r"(\d{1,2}:\d{2}:\d{2})", line)
            if not zeit_match:
                continue

            try:
                zeit = datetime.strptime(zeit_match.group(1), "%H:%M:%S").time()
                zeitpunkt = datetime.combine(datum, zeit)
            except ValueError:
                continue

            if zeitpunkt > jetzt:
                continue

            json_match = re.search(r"\{.*\}", line)
            if not json_match:
                continue

            try:
                data = json.loads(json_match.group(0))
                soc_value = data.get("SOC")
                power_value = data.get("InverterOutputPower")

                if soc_value is None or power_value is None:
                    fehler_zeilen += 1
                    continue

                zeiten.append(zeitpunkt)
                soc.append(soc_value)
                output_power.append(power_value)
            except json.JSONDecodeError:
                fehler_zeilen += 1
                continue

print(f"ℹ️ {fehler_zeilen} fehlerhafte oder unvollständige Zeilen übersprungen.")

if not zeiten:
    print("⚠️ Keine gültigen Datensätze gefunden.")
    exit()

# === In DataFrame umwandeln ===
df = pd.DataFrame({
    "time": zeiten,
    "SOC": soc,
    "Power": output_power
}).sort_values("time")

# Zeitstempel als Index setzen
df.set_index("time", inplace=True)

# Gleitenden Mittelwert über 10 Minuten berechnen
df["Power_avg_10min"] = df["Power"].rolling("10min").mean()

# === Diagramm erstellen ===
fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.set_title("SOC und Inverter Output Power über Zeit (mit 10-Minuten-Mittelwert)")
ax1.set_xlabel("Datum & Uhrzeit")
ax1.grid(True)

# SOC (linke Achse)
ax1.plot(df.index, df["SOC"], label="SOC (%)", color="tab:green"
                                                     "")
ax1.set_ylabel("SOC (%)", color="tab:blue")

# Inverter Output Power (rechte Achse)
ax2 = ax1.twinx()
ax2.plot(df.index, df["Power"], label="Inverter Output Power (W)", color="tab:red", alpha=0.5)
ax2.plot(df.index, df["Power_avg_10min"], label="10-Minuten Mittelwert", color="tab:blue", linewidth=2.5)
ax2.set_ylabel("Inverter Output Power (W)", color="tab:red")

# Legenden kombinieren
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines + lines2, labels + labels2, loc="upper left")

ax1.set_xlim(left=df.index.min(), right=jetzt)
plt.xticks(rotation=45)
plt.tight_layout()

# Diagramm speichern
plt.savefig("inverter_plot.png", dpi=300)
plt.show()
