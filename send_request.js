document.getElementById('floor').addEventListener('change', updateRooms);
document.getElementById('building').addEventListener('change', updateRooms);

function updateRooms() {
    const building = document.getElementById('building').value;
    const floor = document.getElementById('floor').value;
    const roomDropdown = document.getElementById('room');
    roomDropdown.innerHTML = '<option value="">ROOM</option>';

    if (building && floor) {
        for (let i = 1; i <= 10; i++) {
            const roomSuffix = i < 10 ? `0${i}` : `${i}`;
            const roomNumber = `${building}-${floor}${roomSuffix}`;
            const option = document.createElement('option');
            option.value = roomNumber;
            option.text = roomNumber;
            roomDropdown.appendChild(option);
        }
    }
}