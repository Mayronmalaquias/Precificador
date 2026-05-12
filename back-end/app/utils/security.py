def validate_password_strength(password):
    if not password:
        return "Senha e obrigatoria"
    if len(password) < 8:
        return "A senha deve conter no minimo 8 caracteres"
    if password.lower() == password or password.upper() == password:
        return "A senha precisa ter letras maiusculas e minusculas"
    if not any(c.isalpha() for c in password):
        return "A senha precisa ter pelo menos uma letra"
    if not any(c.isdigit() for c in password):
        return "A senha precisa ter pelo menos um numero"
    return None
