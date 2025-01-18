@referral_router.message(lambda message: message.text.strip() in {texts['info_refferal_net'][lang].strip() for lang in texts['info_refferal_net']})
async def referral_network_info(message: Message):
    user_id = message.from_user.id

    # Получаем количество приглашённых пользователей
    referral_count = await get_referral_count(user_id)

    # Используем run_in_executor для вызова синхронной функции
    loop = asyncio.get_event_loop()
    earnings = await loop.run_in_executor(None, get_user_earnings, user_id)

    # Формируем текст сообщения
    info_text = (
        "🤝 Ваша реферальная сеть позволяет вам получать бонусы за приглашённых пользователей!\n\n"
        "📌 Как это работает:\n"
        "1️⃣ Поделитесь своей реферальной ссылкой с друзьями.\n"
        "2️⃣ Когда ваш друг регистрируется, вы получаете бонус на ваш баланс.\n"
        "3️⃣ Чем больше друзей — тем больше бонусов!\n\n"
        "📊 Текущая статистика:\n"
        f"👥 Приглашено пользователей: {referral_count}\n"
        f"💰 Заработано бонусов: {earnings} {CURRENCY}\n\n"
        "Не упустите возможность рассказать друзьям о RaJah.WS и получить больше наград!"
    )

    await message.answer(info_text)
