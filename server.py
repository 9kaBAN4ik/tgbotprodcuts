from fastapi import FastAPI, Form
from pydantic import BaseModel
import hashlib

app = FastAPI()


class PaymentNotification(BaseModel):
    notification_hash: str
    amount: float
    user_id: int
    # Добавьте другие параметры, которые приходят от ЮMoney


@app.post("/payment-notification")
async def payment_notification(notification: PaymentNotification):
    secret_key = "DBA879DAC2E2B56A4386915C842E54B8F3F56CBF47C7F6B668740300D14F5A3D563D7085EA05D6871F2ACD3038FCA70D742B493183936C82BD64CF8A95C8E3E8"


    # Создаем строку для проверки подписи
    data_string = f"amount={notification.amount}&user_id={notification.user_id}" + secret_key
    calculated_hash = hashlib.md5(data_string.encode('utf-8')).hexdigest()

    if notification.notification_hash == calculated_hash:
        # Обработка платежа
        update_balance(notification.user_id, notification.amount)
        return {"status": "OK"}
    else:
        return {"status": "Invalid signature"}, 400


def update_balance(user_id, amount):
    # Логика обновления баланса пользователя
    pass
