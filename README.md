# ¿Qué se quemó en el Perú? Cobertura del suelo de las áreas quemadas, 2013–2024

**Autor:** [Tu nombre completo]. [Curso], [Universidad], [fecha].

**Página:** [¿Qué se quemó en el Perú?](https://TU-USUARIO.github.io/que-se-quemo-peru/), un recorrido con cifras y gráficos de qué cobertura tenía el área quemada.

## Pregunta

¿Qué cobertura del suelo tenía el área quemada en todo el Perú entre 2013 y 2024: bosque, pastizal o terreno agropecuario? ¿Cómo cambia según la región natural, el departamento y el mes? ¿Qué valor económico implica cada hectárea según su cobertura?

## Datos

| Dato | Fuente | Uso |
| --- | --- | --- |
| Área quemada por primera vez y su cobertura, 2013–2024 | MapBiomas Perú, MapBiomas Fuego Perú, Colección 1 (Landsat, 30 m, CC-BY) | Cifras nacionales de la página |
| Severidad dNBR | Key y Benson (2006), FIREMON, USDA Forest Service | Umbrales de la calculadora |
| Cobertura de 10 m | ESA WorldCover (2020 v100, 2021 v200) | Método para medir un incendio concreto |
| Nubes y sombras | Sentinel-2 L2A, capa SCL | Método para medir un incendio concreto |
| Focos de calor | NASA FIRMS, VIIRS | Método para medir un incendio concreto |
| Área quemada acumulada 2013–2024 (ráster 0/1, 30 m) | MapBiomas Fuego Perú, Colección 1 | Mapa 3D |
| Límites departamentales | GADM 4.1 (`gadm41_PER.gpkg`) | Mapa 3D |

Las cifras usadas están en `data/mapbiomas-fuego-peru.json`, cada una con su fuente. Los datos del mapa 3D están en `data/geo-mapa3d.json`.

## Método

Cifras nacionales: se toman de MapBiomas Fuego Perú y se agrupan en cinco coberturas (agropecuario, pastizal y herbazal, bosque, matorral, otras). Las hectáreas por cobertura son aproximadas: porcentaje por 2,3 millones de hectáreas.

Para un incendio concreto, el camino es:

1. Bajar los focos VIIRS de los últimos 7 días y ubicar el incendio.
2. Leer Sentinel-2 L2A solo en esa zona, una imagen antes y otra después con poca nube.
3. Calcular NBR y dNBR, enmascarar nubes con SCL y clasificar la severidad.
4. Cruzar el área quemada con ESA WorldCover (bosque 10, matorral 20, pastizal 30, cultivo 40).
5. Contar hectáreas por cobertura, severidad y distrito (cada píxel de 10 m son 0,01 ha).
6. Multiplicar por un valor por hectárea con fuente.

## Mapa 3D

El ráster acumulado marca cada píxel de 30 m como quemado o no quemado al menos una vez entre 2013 y 2024 (suma: 2 305 073 ha). `pipeline/preparar_mapa3d.py` lo procesa en cuatro pasos:

1. Lee el GeoTIFF (teselas LZW) con un lector propio, sin GDAL, y suma los píxeles quemados en bloques de 8 × 8 (240 m). La hectárea por píxel se corrige por la latitud.
2. Asigna cada bloque a un departamento (GADM, capa `ADM_ADM_1`) y suma las hectáreas. La provincia de Lima se une a Lima. Suma de departamentos: 2 304 928 ha, el 99,99 % del total.
3. Simplifica los límites con Douglas-Peucker (0,012°, cerca de 1 km) y descarta islotes menores a unos 45 km².
4. Agrupa los bloques en celdas de unos 10 km para las columnas (se guardan las de 30 ha o más: 98,9 % del área).

La escena se dibuja en un `<canvas>` con proyección propia, sin librerías. Se puede girar, inclinar, exagerar la altura y leer cada departamento o celda.

Comprobación: las hectáreas medidas coinciden con las publicadas por MapBiomas (2013–2024) dentro de ±0,6 % en siete de los diez primeros departamentos. Las mayores diferencias son Huánuco (−3,6 %), Ucayali (+2,2 %) y Junín (−1,1 %), que pueden venir de los límites usados o del método.

```
python pipeline/preparar_mapa3d.py RUTA_AL_TIF RUTA_AL_GPKG
```

Requiere `numpy`, `pillow` y `tifffile`. Los archivos de entrada no se suben al repositorio por su tamaño.

## Limitaciones

- El mapa 3D usa la capa acumulada, que no separa los años. La evolución año por año necesita los ráster anuales de MapBiomas Fuego.

- El total de 2,3 millones de hectáreas es área quemada por primera vez. Una infografía del mismo proyecto muestra 1,6 millones como área neta.
- Los meses se asignan según el orden de la infografía de MapBiomas; el 79 % entre agosto y noviembre sí está dicho de forma explícita.
- La serie llega hasta 2024.
- La cobertura de MapBiomas (30 m) y la de WorldCover (10 m) no son idénticas. No se mezclan en las cifras.

## Estructura

```
.
├── docs/
│   └── index.html                  Página completa (HTML, CSS y JavaScript en un archivo)
├── data/
│   ├── mapbiomas-fuego-peru.json   Cifras usadas, con su fuente
│   └── geo-mapa3d.json             Departamentos, hectáreas y columnas del mapa 3D
├── pipeline/
│   ├── preparar_mapa3d.py          Del ráster y los límites al JSON del mapa 3D
│   ├── lzwtif.py                   Lector de GeoTIFF con teselas LZW
│   ├── geoproc.py                  Lectura de GeoPackage y simplificación de líneas
│   └── requirements.txt
├── .gitignore
└── README.md
```

## Ver la página

Abre `docs/index.html` con doble clic. Con internet carga la tipografía de Google Fonts; sin internet usa la del sistema. Navega con la barra superior o con las flechas ← → del teclado.

## Fuentes

- MapBiomas Perú: https://peru.mapbiomas.org
- Key, C. H. y Benson, N. C. (2006). Landscape Assessment (LA). En FIREMON, USDA Forest Service, RMRS-GTR-164-CD.
- Zanaga, D. et al. (2022). ESA WorldCover 10 m 2021 v200. https://doi.org/10.5281/zenodo.7254221
- GADM 4.1, límites administrativos del Perú: https://gadm.org
- Mongabay Latam (diciembre de 2025): https://es.mongabay.com/2025/12/incendios-forestales-millones-hectareas-quemadas-peru/

## Licencia

Los datos son de MapBiomas Perú (CC-BY): cita siempre la fuente. Agrega la licencia que prefieras para el código de la página.
