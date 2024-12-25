from app import db, User, Apartment

# Изменение пользователя admin
admin_user = User.query.filter_by(username="admin").first()
admin_user.type = "a"  # Устанавливаем тип 'a'
db.session.commit()

# Добавление 10 квартир
for i in range(1, 11):
    apartment = Apartment(
        address=f"Address {i}",
        rooms=i % 4 + 1,  # От 1 до 4 комнат
        price=100000 + i * 1000,  # Примерная цена
        description=f"Description for apartment {i}",
        type="rent" if i % 2 == 0 else "buy"  # Тип: rent/buy
    )
    db.session.add(apartment)

db.session.commit()  # Сохраняем изменения
print("10 apartments added!")