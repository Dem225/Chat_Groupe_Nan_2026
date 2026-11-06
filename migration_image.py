
import sqlite3

connection = sqlite3.connect("chat.db")

columns = [
    row[1]
    for row in connection.execute("PRAGMA table_info(messages)")
]

if "image_path" not in columns:
    connection.execute(
        "ALTER TABLE messages ADD COLUMN image_path VARCHAR(500)"
    )
    connection.commit()
    print("Colonne image_path ajoutée avec succès.")
else:
    print("La colonne image_path existe déjà.")

connection.close()
