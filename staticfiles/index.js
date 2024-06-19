// Function to update the current time on the web page
function updateCurrentTime() {
    const currentTimeElement = document.getElementById('currentTime');
    currentTimeElement.innerText = `Date: ${new Date().toLocaleString()}`;
}

window.addEventListener('DOMContentLoaded', updateCurrentTime);

const socket = new WebSocket('ws://' + window.location.host + '/ws/sensor-data/');

socket.onopen = function(event) {
    console.log('WebSocket connected.');
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateSensorData(data);
};

function updateSensorData(data) {
    if (data.sensor_type === 'DHT22') {
        document.getElementById('temperature').innerText = `Temperature: ${data.value.temC.toFixed(2)}°C`;
        document.getElementById('humidity').innerText = `Humidity: ${data.value.humi.toFixed(2)}%`;
    } else if (data.sensor_type === 'MQ135') {
        document.getElementById('mq135Value').innerText = `${data.value.value.toFixed(2)}`;
        updateAirQuality(document.getElementById('mq135Quality'), data.value.quality);
    } else if (data.sensor_type === 'pmValue') {
        document.getElementById('pmValue').innerText = `PM_1p0 : ${data.value.PM_1p0.toFixed(2)},
            PM_2p5 : ${data.value.PM_2p5.toFixed(2)},
            PM_4p0 : ${data.value.PM_4p0.toFixed(2)},
            PM_10p0 : ${data.value.PM_10p0.toFixed(2)}`;
        updateAirQuality(document.getElementById('pmQuality'), data.value.quality);

    }
}

function updateAirQuality(element, quality) {
    element.innerText = `${quality}`;
    element.className = 'sensor-quality'; 
    switch (quality.toLowerCase()) {
        case 'good':
            element.classList.add('quality-good');
            break;
        case 'moderate':
            element.classList.add('quality-moderate');
            break;
        case 'poor':
            element.classList.add('quality-poor');
            break;
        case 'unhealthy':
            element.classList.add('quality-unhealthy');
            break;
        case 'very unhealthy':
            element.classList.add('quality-very-unhealthy');
            break;
        case 'Hazardous':
            element.classList.add('quality-Hazardous');
            break;
        default:
            element.classList.add('quality-unknown'); 
    }
}
