import re
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import glob
import os

# === Einstellungen ===
ordner = "log"
dateimuster = "Offgrid*.log"

# Heute und vor 1 Tag (letzte 2 Tage insgesamt)
heute = datetime.now().date()
vor_1_tag = heute - timedelta(days=1)

zeiten = []
soc = []
output_power = []

dateiliste = sorted(glob.glob(os.path.join(ordner, dateimuster)))

# Filter: nur Dateien der letzten 2 Tage
dateiliste_filtered = []
for dateiname in dateiliste:
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", dateiname)
    if date_match:
        datum = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        if vor_1_tag <= datum <= heute:
            dateiliste_filtered.append(dateiname)

if not dateiliste_filtered:
    print(f"⚠️ Keine Dateien der letzten 2 Tage gefunden in: {os.path.abspath(ordner)}")
    exit()
else:
    print(f"📂 {len(dateiliste_filtered)} Dateien der letzten 2 Tage gefunden, lese ein...")

jetzt = datetime.now()
fehler_zeilen = 0

for dateiname in dateiliste_filtered:
    print(f"→ Lese {os.path.basename(dateiname)}")

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", dateiname)
    if date_match:
        datum = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
    else:
        datum = heute

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
fig.patch.set_facecolor('#2e2e2e')  # dunkelgrauer Hintergrund
ax1.set_facecolor('#2e2e2e')
ax1.set_title("SOC und Inverter Output Power über Zeit (mit 10-Minuten-Mittelwert)", color="white")
ax1.set_xlabel("Datum & Uhrzeit", color="white")
ax1.tick_params(axis='x', colors='white')
ax1.tick_params(axis='y', colors='white')
ax1.grid(True, color='gray', linestyle='--', alpha=0.5)

# SOC (linke Achse)
ax1.plot(df.index, df["SOC"], label="SOC (%)", color="#00FF00", linewidth=2)  # leuchtgrün
ax1.set_ylabel("SOC (%)", color="#00FF00")

# Inverter Output Power (rechte Achse)
ax2 = ax1.twinx()
ax2.plot(df.index, df["Power"], label="Inverter Output Power (W)", color="#FF4500", alpha=0.7, linewidth=1.5)  # orangerot
ax2.plot(df.index, df["Power_avg_10min"], label="10-Minuten Mittelwert", color="#1E90FF", linewidth=2.5)  # hellblau
ax2.set_ylabel("Inverter Output Power (W)", color="#1E90FF")
ax2.tick_params(axis='y', colors='white')

# Legenden kombinieren
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines + lines2, labels + labels2, loc="upper left", facecolor='#3e3e3e', edgecolor='white', labelcolor='white')

ax1.set_xlim(left=df.index.min(), right=jetzt)
plt.xticks(rotation=45, color='white')
plt.tight_layout()

# Diagramm speichern
plt.savefig("static/resource/inverter_plot.png", dpi=300, facecolor=fig.get_facecolor())
plt.show()