document.addEventListener("DOMContentLoaded", function() {
    // Пример простой интерактивности (можно добавить фильтрацию)
    const productRows = document.querySelectorAll(".product-list tr");

    // Добавим подсветку строки при наведении
    productRows.forEach(row => {
        row.addEventListener("mouseover", () => {
            row.style.backgroundColor = "#ecf0f1";
        });
        row.addEventListener("mouseout", () => {
            row.style.backgroundColor = "";
        });
    });
});
