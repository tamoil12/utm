from flask import Flask, render_template, request, redirect, url_for
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pyproj import Proj, Transformer
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def get_exif_data(image_path):
    image = Image.open(image_path)
    exif_data = image._getexif()

    if exif_data is None:
        return None

    exif = {}
    gps_data = {}

    for tag, value in exif_data.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "DateTime":
            exif["Fecha y Hora"] = value
        elif decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                gps_data[sub_decoded] = value[t]

    # Convertir latitud y longitud a grados decimales si están presentes
    if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
        lat = convert_to_degrees(gps_data["GPSLatitude"])
        lon = convert_to_degrees(gps_data["GPSLongitude"])

        # Ajustar el signo según GPSLatitudeRef y GPSLongitudeRef
        if gps_data.get("GPSLatitudeRef") == "S":  # Latitud Sur
            lat = -lat
        if gps_data.get("GPSLongitudeRef") == "W":  # Longitud Oeste
            lon = -lon

        exif["Latitud"] = lat
        exif["Longitud"] = lon

        # Determinar la zona UTM y el hemisferio
        zona, hemisferio, zona_utm = determinar_zona_utm(lat, lon)
        exif["Zona UTM"] = zona_utm
        exif["Hemisferio"] = hemisferio

        # Convertir a UTM usando la zona correcta
        transformer = Transformer.from_crs("epsg:4326", f"epsg:327{zona}", always_xy=True) if hemisferio == "Sur" else Transformer.from_crs("epsg:4326", f"epsg:326{zona}", always_xy=True)
        x, y = transformer.transform(lon, lat)
        exif["UTM_Easting"] = x
        exif["UTM_Northing"] = y

    return exif

def convert_to_degrees(value):
    d = float(value[0].numerator) / float(value[0].denominator) if hasattr(value[0], 'numerator') else value[0]
    m = float(value[1].numerator) / float(value[1].denominator) if hasattr(value[1], 'numerator') else value[1]
    s = float(value[2].numerator) / float(value[2].denominator) if hasattr(value[2], 'numerator') else value[2]

    return d + (m / 60.0) + (s / 3600.0)

def determinar_zona_utm(lat, lon):
    zona = int((lon + 180) / 6) + 1
    hemisferio = 'Norte' if lat >= 0 else 'Sur'
    zona_utm = f"{zona}{'N' if lat >= 0 else 'S'}"
    return zona, hemisferio, zona_utm

@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        
        # Obtener la fecha personalizada ingresada por el usuario
        custom_date = request.form.get("custom_date", "").strip()
        
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            exif_data = get_exif_data(file_path)
            return render_template('index.html', image_url=file.filename, exif_data=exif_data, custom_date=custom_date)

    return render_template('index.html', exif_data=None)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Obtener el puerto de la variable de entorno 'PORT' que Render configura automáticamente
    port = int(os.environ.get('PORT', 5000))
    
    # Ejecutar la aplicación en 0.0.0.0 en lugar de 127.0.0.1 y usar el puerto asignado
    app.run(host='0.0.0.0', port=port, debug=True)

