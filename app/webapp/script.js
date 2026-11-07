
const tg = window.Telegram.WebApp;
const API_URL = "https://beauty-studio-production-148d.up.railway.app";

tg.ready();
tg.expand();

let selected = null;

const modal = document.getElementById("modal");
const selectedService = document.getElementById("selectedService");

// Загружаем услуги с Railway
async function loadServices() {
    const list = document.querySelector(".list");

    try {
        const response = await fetch(`${API_URL}/services`);

        if (!response.ok) {
            throw new Error("Ошибка загрузки услуг");
        }

        const services = await response.json();

        list.innerHTML = "";

        services.forEach(service => {
            const button = document.createElement("button");

            button.className = "service";
            button.dataset.name = service.name;
            button.dataset.price = service.price;
            button.dataset.time = service.duration;

            button.innerHTML = `
                <span class="icon">✂</span>
                <span>
                    <b>${service.name}</b>
                    <small>${service.duration} мин · ${service.price} ₽</small>
                </span>
            `;

            list.appendChild(button);
        });

        connectServices();
    } catch (error) {
        console.error(error);
        list.innerHTML = "<p>Не удалось загрузить услуги</p>";
    }
}

// Выбор услуги
function connectServices() {
    document.querySelectorAll(".service").forEach(button => {
        button.onclick = () => {
            selected = {
                name: button.dataset.name,
                price: button.dataset.price,
                time: button.dataset.time
            };

            selectedService.textContent =
                selected.name + " — " + selected.price + " ₽";

            modal.hidden = false;
        };
    });
}

// Закрытие окна
document.getElementById("close").onclick = () => {
    modal.hidden = true;
};

// Запись
document.getElementById("book").onclick = () => {
    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();

    if (!selected) {
        alert("Сначала выберите услугу");
        return;
    }

    if (!name || !phone) {
        alert("Заполните имя и телефон");
        return;
    }

    const booking = {
        service: selected.name,
        price: selected.price,
        time: selected.time,
        name: name,
        phone: phone
    };

    if (tg.initData) {
        tg.sendData(JSON.stringify(booking));
    } else {
        alert("Демо-запись создана! Откройте приложение через Telegram.");
    }

    modal.hidden = true;
};

// Запуск
document.addEventListener("DOMContentLoaded", loadServices);
