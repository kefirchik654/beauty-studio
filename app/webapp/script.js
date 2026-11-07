
const shade = document.getElementById("shade");
const details = document.getElementById("details");
const nameInput = document.getElementById("name");
const phoneInput = document.getElementById("phone");
const sendButton = document.getElementById("send");

let selectedService = null;

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

document.querySelectorAll(".service").forEach((button) => {
  button.addEventListener("click", () => {
    selectedService = {
      name: button.dataset.name,
      price: button.dataset.price,
      time: button.dataset.time
    };

    details.textContent =
      `${selectedService.name} — ${selectedService.price} ₽, ${selectedService.time} минут`;

    shade.hidden = false;
  });
});

document.getElementById("close").addEventListener("click", () => {
  shade.hidden = true;
});

shade.addEventListener("click", (event) => {
  if (event.target === shade) {
    shade.hidden = true;
  }
});

sendButton.addEventListener("click", () => {
  const clientName = nameInput.value.trim();
  const phone = phoneInput.value.trim();

  if (!clientName || !phone || !selectedService) {
    alert("Заполни имя и телефон");
    return;
  }

  const booking = {
    name: clientName,
    phone: phone,
    service: selectedService.name,
    price: selectedService.price,
    time: selectedService.time
  };

  if (tg) {
    tg.sendData(JSON.stringify(booking));
  } else {
    alert("Демонстрация: заявка заполнена!");
    console.log(booking);
  }

  shade.hidden = true;
});
