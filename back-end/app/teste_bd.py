from sqlalchemy import create_engine, text
from config import Config  # ajuste se o nome for outro

print("URI usada:")
print(repr(Config.SQLALCHEMY_DATABASE_URI))

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=True)

with engine.connect() as conn:
    res = conn.execute(text("""
        SELECT 
            current_setting('server_encoding') AS server_encoding,
            current_setting('client_encoding') AS client_encoding,
            current_setting('lc_messages')     AS lc_messages;
    """))
    row = res.fetchone()
    print("Encodings:")
    print("server_encoding:", row.server_encoding)
    print("client_encoding:", row.client_encoding)
    print("lc_messages    :", row.lc_messages)
