// rooms.js

let rooms = []; // Globale Variable für die geladenen Räume

// Räume vom Backend laden
async function fetchRooms() {
    try {
        const response = await fetch('/api/rooms');
        rooms = await response.json();
        renderRooms();
    } catch (err) {
        console.error("Fehler beim Laden der Räume:", err);
    }
}

// Tabelle rendern
function renderRooms() {
    const tbody = document.querySelector("#room-table tbody");
    tbody.innerHTML = "";

    rooms.forEach(room => {
        room.slots.forEach((slot, index) => {
            const tr = document.createElement("tr");
            tr.setAttribute("data-room", room.name);
            tr.setAttribute("data-slot", index);

            tr.innerHTML = `
                <td>
                    <span class="lamp ${slot.active ? 'green' : ''}"></span>
                    <span class="lamp ${slot.heating ? 'on' : ''}"></span>
                    ${room.name}
                </td>
                <td><strong>${room.current.toFixed(1)} °C</strong></td>
                <td><input type="time" value="${slot.time}" onchange="updateSlotTime('${room.name}', ${index}, this.value)"></td>
                <td><input type="number" step="0.5" value="${slot.temp}" onchange="updateSlotTemp('${room.name}', ${index}, this.value)"></td>
                <td class="days-cell"></td>
                <td>
                    <button onclick="deleteSlot('${room.name}', ${index})">🗑️</button>
                </td>
            `;

            tbody.appendChild(tr);

            // Dropdown für Tage
            const daysCell = tr.querySelector(".days-cell");
            const select = createDaysDropdown(slot.days);
            select.addEventListener("change", (e) => updateSlotDays(room.name, index, e.target.value));
            daysCell.appendChild(select);
        });

        // Button zum Hinzufügen eines neuen Slots
        const addTr = document.createElement("tr");
        addTr.innerHTML = `
            <td colspan="6" style="text-align:right;">
                <button onclick="addSlot('${room.name}')">Neuen Slot hinzufügen</button>
                <button onclick="saveAllSlots('${room.name}')">Alle Slots speichern</button>
            </td>
        `;
        tbody.appendChild(addTr);
    });
}

function deleteSlot(roomName, slotIndex) {
    const room = rooms.find(r => r.name === roomName);
    if (!room) return;

    // Bestätigungsdialog
    if (!confirm(`Slot ${slotIndex + 1} im Raum "${roomName}" wirklich löschen?`)) return;

    room.slots.splice(slotIndex, 1);  // Slot entfernen
    renderRooms();                     // Tabelle neu rendern
}


// Slot-Felder in rooms aktualisieren
function updateSlotTime(roomName, slotIndex, value) {
    const room = rooms.find(r => r.name === roomName);
    if (room) room.slots[slotIndex].time = value;
}

function updateSlotTemp(roomName, slotIndex, value) {
    const room = rooms.find(r => r.name === roomName);
    if (room) room.slots[slotIndex].temp = parseFloat(value);
}

function updateSlotDays(roomName, slotIndex, value) {
    const room = rooms.find(r => r.name === roomName);
    if (room) room.slots[slotIndex].days = value;
}

// Alle Slots eines Raums speichern
async function saveAllSlots(roomName) {
    const room = rooms.find(r => r.name === roomName);
    if (!room) return;

    const profile = { name: roomName, slots: room.slots };

    try {
        const response = await fetch(`/api/rooms/${roomName}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profile)
        });
        const result = await response.json();
        if (result.status === "ok") alert(`Alle Slots für "${roomName}" gespeichert!`);
        else alert("Fehler: " + result.message);
    } catch (err) {
        console.error("Fehler beim Speichern:", err);
        alert("Speicherfehler. Siehe Konsole.");
    }
}

// Neuen Slot hinzufügen
function addSlot(roomName) {
    const room = rooms.find(r => r.name === roomName);
    if (!room) return;

    const newSlot = { time: "00:00", temp: 20.0, days: "1-7" };
    room.slots.push(newSlot);
    renderRooms();
}

// Hilfsfunktion für das Tage-Dropdown
function createDaysDropdown(selectedDays) {
    const options = [
        "Mo","Di","Mi","Do","Fr","Sa","So",
        "1-7","1-5","6-7"
    ];
    const select = document.createElement("select");
    options.forEach(opt => {
        const option = document.createElement("option");
        option.value = opt;
        option.textContent = opt;
        if (opt === selectedDays) option.selected = true;
        select.appendChild(option);
    });
    return select;
}

// DOM ready
document.addEventListener("DOMContentLoaded", fetchRooms);
