document.addEventListener("DOMContentLoaded", () => {

    function updateGraphics(batI, solarPower) {
        //console.log(`Update Graphics: ${batI}, ${solarPower}`)
        const batIElement = document.getElementById("batI");
        if (batIElement) batIElement.style.color = batI < 0 ? "red" : "green";

        const maxPower = 3000;
        const pointerElement = document.getElementById("tachometer-pointer");
        if (pointerElement) {
            const angle = (solarPower / maxPower) * 180;
            pointerElement.style.transform = `rotate(${angle - 90}deg)`;
        }

        const arrow = document.getElementById("arrow");
        if (arrow) {
            if (batI > 0) {
                arrow.innerHTML = "&#8593;";
                arrow.style.color = "green";
            } else {
                arrow.innerHTML = "&#8595;";
                arrow.style.color = "red";
            }
        }
    }

    async function updateInverterData() {
        try {
            const res = await fetch('/api/inverterValues');
            const supply = await fetch('/api/get_supplyState')

            if (200 != res.status){
                console.error("failed to fetch data for inverterValues: " + res.statusText)
                return
            }
            if (200 != supply.status){
                console.error("failed to fetch data for get_supplyState: " + res.statusText)
                return
            }
            const json = await res.json();
            const json2 = await supply.json()
            const data = json.values;
            //console.log(JSON.stringify(data))
            //console.log(JSON.stringify(json2))

            // 🔋 Inverterdaten anzeigen
            document.getElementById('batV').textContent = data.BatteryVoltage.toFixed(1) + ' V';
            document.getElementById('batI').textContent = data.BatteryCurrent.toFixed(1) + ' A';
            document.getElementById('pan1I').textContent = data.CurrentSolar1.toFixed(1) + ' A';
            document.getElementById('pan2I').textContent = data.CurrentSolar2.toFixed(1) + ' A';
            document.getElementById('sol1V').textContent = data.VoltageSolar1.toFixed(1) + ' V';
            document.getElementById('sol2V').textContent = data.VoltageSolar2.toFixed(1) + ' V';
            document.getElementById('sumP').textContent = data.InverterOutputPower.toFixed(0) + ' W';
            document.getElementById('solar1Power').textContent = data.PowerSolar1.toFixed(0) + ' W';
            document.getElementById('solar2Power').textContent = data.PowerSolar2.toFixed(0) + ' W';
            document.getElementById('soc').textContent = data.SOC.toFixed(0) + ' %';
            document.getElementById('solarSupply').textContent = json2.supplyState;

            // Batteriegrafik aktualisieren
            const batteryLevel = document.getElementById('battery-level');
            const soc = parseFloat(data.SOC);
            const solarPower = parseInt(data.PowerSolar1) + parseInt(data.PowerSolar2)
            if (batteryLevel) {
                batteryLevel.style.height = soc + '%';
                batteryLevel.style.backgroundColor = soc < 20 ? 'red' : 'green';
            }

            document.getElementById('soc-display').textContent = soc + '%';
            document.getElementById('tachometer-label').textContent = solarPower + ' W';
            updateGraphics(parseFloat(data.BatteryCurrent), solarPower);

        } catch (err) {
            console.error("Fehler beim Abrufen der Inverterdaten:", err);
        }
    }

    async function updateConsumers() {
        try {
            const res = await fetch('/api/get_consumers');
            const json = await res.json();
            let html = '';
            json.devices.forEach(dev => {
                html += `<tr>
                            <td>${dev.name}</td>
                            <td>${dev.mode}</td>
                            <td>
                                <button class="device-button" data-device="${dev.name}" data-mode="ON">ON</button>
                                <button class="device-button" data-device="${dev.name}" data-mode="OFF">OFF</button>
                                <button class="device-button" data-device="${dev.name}" data-mode="AUTO">AUTO</button>
                            </td>
                         </tr>`;
            });
            document.getElementById('device-table').innerHTML = html;
        } catch (err) {
            console.error("Fehler beim Abrufen der Verbraucher:", err);
        }
    }

    // Klick-Handler für Geräte
    document.getElementById('device-table').addEventListener('click', e => {
        const target = e.target;
        if (target.classList.contains('device-button')) {
            const mode = target.dataset.mode;
            const name = target.dataset.device;
            fetch('/api/consumer/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, mode })
            })
            .then(res => res.json())
            .then(data => console.log('Gerät geändert:', data))
            .catch(err => console.error(err));
        }
    });

    // Alle paar Sekunden alles aktualisieren
    async function updateAll() {
        await updateInverterData();
        await updateConsumers();
        await updateTemperatures();
    }

    updateAll();
    setInterval(updateAll, 1000);
});

async function updateTemperatures() {
    try {
        const res = await fetch("/api/get_temperatures");
        const data = await res.json();
        //console.log(`received temperatur data: ${JSON.stringify(data)}`)

        let html = "<tbody><tr><td><strong>Name</strong></td><td><strong>Temperatur</strong></td></tr></tbody>";

        data.temperatures.forEach(t => {
            //console.log(`temperature : ${JSON.stringify(t)}`)
            let tempDisplay = "—";
            if (t.temp !== null && !isNaN(t.temp)) tempDisplay = t.temp.toFixed(1) + "°C";
            html += `<tr><td>${t.name}</td><td>${tempDisplay}</td></tr>`;
        });
        //console.log(html)

        // Hier den Container auswählen, z.B. wo du die Tabelle haben willst
        const container = document.querySelector("#temperature-table");
        if (container) container.innerHTML = html;

    } catch (err) {
        console.error("Fehler beim Abrufen der Temperaturen:", err);
    }
}

