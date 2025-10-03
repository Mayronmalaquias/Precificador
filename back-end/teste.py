from geopy.geocoders import Nominatim
import time

geolocator = Nominatim(user_agent="meu_app")

def obter_coordenadas(cep):
    try:
        # Formata o CEP como string e envia diretamente
        location = geolocator.geocode(f"{cep}, Brasil")
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Nenhuma coordenada encontrada para o CEP: {cep}")
    except Exception as e:
        print(f"Erro ao buscar coordenadas para o CEP {cep}: {e}")
    return None, None

lat, long = obter_coordenadas("72548609")
print(f"{lat} && {long}")
