#Только для flask shell

from app import db, User
user = User.query.filter_by(username="admin").first()
if user:
     user.type = 'a'
     db.session.commit()
     print("Тип пользователя admin успешно изменён.")
else:
     print("Пользователь admin не найден.")