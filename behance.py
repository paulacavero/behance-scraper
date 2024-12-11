from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime
import csv
import re

# Inicializa el navegador de Selenium
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Carga la página
url = 'https://www.behance.net/joblist?tracking_source=nav20' #Link to the Behance job list
driver.get(url)

# Configuración de la cantidad de ofertas a revisar y días recientes para filtrar
dias_recientes = 30
numero_deseado = 600  # Total de ofertas a revisar en la web
enlaces_revisados = []  # Todos los enlaces revisados, sin importar el filtro de días
enlaces_encontrados = []  # Enlaces que cumplen con el filtro de 30 días
ofertas_guardadas = []
ciclos_sin_nuevos_enlaces = 0  # Contador para detectar cuando ya no cargan nuevas ofertas

try:
    # Espera hasta 20 segundos para que aparezca el primer enlace de oferta
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "JobCard-jobCardLink-Ywm"))
    )

    # Bucle de desplazamiento para capturar hasta numero_deseado de ofertas
    while len(enlaces_revisados) < numero_deseado and ciclos_sin_nuevos_enlaces < 5:
        # Ejecuta el desplazamiento hacia abajo y espera para cargar contenido nuevo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(5)  # Aumenta el tiempo para asegurar carga de nuevos elementos

        # Obtiene el HTML de la página actual
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Guarda la cantidad de enlaces revisados antes de esta página
        enlaces_previos = len(enlaces_revisados)

        # Procesa cada oferta y extrae el enlace
        for job_card in soup.find_all('a', class_='JobCard-jobCardLink-Ywm'):
            link = job_card['href']
            full_url = f"https://www.behance.net{link}"
            
            # Verifica si ya hemos revisado este enlace
            if full_url not in enlaces_revisados:
                enlaces_revisados.append(full_url)  # Agrega a la lista de revisados

                # Ahora revisa si cumple con `dias_recientes`
                aria_label = job_card.get('aria-label', '')
                dias_publicado = None
                if "hace" in aria_label:
                    if re.search(r'(\d+)\s*d[ií]as?', aria_label):  # Coincide con "hace X días"
                        dias_publicado = int(re.search(r'(\d+)\s*d[ií]as?', aria_label).group(1))
                    elif re.search(r'un\s*mes', aria_label):  # Coincide con "hace un mes"
                        dias_publicado = 30
                    elif re.search(r'(\d+)\s*meses?', aria_label):  # Coincide con "hace X meses"
                        dias_publicado = int(re.search(r'(\d+)\s*meses?', aria_label).group(1)) * 30
                    elif re.search(r'(\d+)\s*horas?', aria_label):  # Coincide con "hace X horas"
                        dias_publicado = 0  # Publicado hoy mismo si es en horas

                # Verifica en `JobCard-time-Cvz` si `aria-label` no es suficiente
                if dias_publicado is None:
                    tiempo_elemento = job_card.find_next('span', class_='JobCard-time-Cvz')
                    if tiempo_elemento:
                        tiempo_texto = tiempo_elemento.text.strip()
                        if re.search(r'(\d+)\s*d[ií]as?', tiempo_texto):
                            dias_publicado = int(re.search(r'(\d+)\s*d[ií]as?', tiempo_texto).group(1))
                        elif re.search(r'un\s*mes', tiempo_texto):
                            dias_publicado = 30
                        elif re.search(r'(\d+)\s*meses?', tiempo_texto):
                            dias_publicado = int(re.search(r'(\d+)\s*meses?', tiempo_texto).group(1)) * 30
                        elif re.search(r'(\d+)\s*horas?', tiempo_texto):
                            dias_publicado = 0

                # Agrega a `enlaces_encontrados` solo si cumple con el filtro de días
                if dias_publicado is not None and dias_publicado <= dias_recientes:
                    enlaces_encontrados.append(full_url)

        # Verifica si se encontraron nuevos enlaces en este ciclo
        if len(enlaces_revisados) == enlaces_previos:
            ciclos_sin_nuevos_enlaces += 1  # Incrementa si no hubo nuevos enlaces
        else:
            ciclos_sin_nuevos_enlaces = 0  # Restablece si hubo nuevos enlaces

    # Muestra el total de enlaces revisados y los enlaces recientes encontrados
    print(f"Total de enlaces revisados: {len(enlaces_revisados)}")
    print(f"Total de enlaces recientes encontrados (menos de {dias_recientes} días): {len(enlaces_encontrados)}")

    # Accede a cada enlace reciente y verifica la palabra clave "Blender"
    for full_url in enlaces_encontrados:
        driver.get(full_url)
        sleep(2)  # Espera a que cargue la página de la oferta

        # Extrae el HTML de la oferta y analiza el contenido
        job_html = driver.page_source
        job_soup = BeautifulSoup(job_html, 'html.parser')

        # Verifica la palabra clave en la descripción de la oferta
        if "Blender" in job_soup.text:
            print(f"Oferta cumple la condición: {full_url}")

            # Extrae el link y el nombre de la empresa
            link_empresa_guardado = None
            nombre_empresa = None
            link_empresa = job_soup.find('a', class_='JobDetailContent-companyNameLink-EUx')
            if link_empresa:
                link_empresa_guardado = link_empresa["href"]
                nombre_empresa = link_empresa.text.strip()
                # Elimina el texto extra "se abre en una pestaña nueva" si está presente
                nombre_empresa = nombre_empresa.replace("se abre en una pestaña nueva", "").strip()

            # Guarda los datos en la lista de ofertas
            ofertas_guardadas.append({
                'link_oferta': full_url,
                'link_empresa': link_empresa_guardado,
                'nombre_empresa': nombre_empresa
            })

    print(f'Lista de ofertas guardadas: {ofertas_guardadas}')

finally:
    # Cierra el navegador al final
    driver.quit()

# Guardado en CSV
csv_filename = 'behance_jobs.csv'  #Add your local path to save the CSV file
enlaces_existentes = set()

try:
    with open(csv_filename, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            enlaces_existentes.add(row['link_oferta'])
except FileNotFoundError:
    print('Documento no encontrado')
    pass

with open(csv_filename, mode='a', newline='', encoding='utf-8-sig') as file:
    fieldnames = ['link_oferta', 'nombre_empresa', 'link_empresa', 'fecha_almacenada']
    writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=',')
    if file.tell() == 0:
        writer.writeheader()

    for oferta in ofertas_guardadas:
        if oferta['link_oferta'] not in enlaces_existentes:
            oferta['fecha_almacenada'] = datetime.now().strftime('%Y-%m-%d')
            writer.writerow(oferta)

