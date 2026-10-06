from app.models.database import Base, engine
from app.models import models  # noqa: F401 - registers the tables above

Base.metadata.create_all(bind=engine)
print("Database tables created successfully.")
