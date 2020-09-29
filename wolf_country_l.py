#!/usr/bin/env python3

import requests
import json
import os.path
import sys
import pyproj
from functools import partial
from shapely.geometry import Point, Polygon, MultiPolygon

# Координаты волков
URLWOLF = 'http://riistahavainnot.fi/json/grid?bbox=-1176112,6272256,2076112,8127744'

# Координаты страны
URLCOUNTRY = 'http://moredata.pythonhelp.ru/countries/countries.geojson'

# Файл с координатами стран
JSONFILE = '.country.json'


def create_polygon(json_data, *, country):
    """
       Получает структуру json с координатами страны, именованный
       аргумент list (countries)  с именем стран,
       при обнаружении страны в json
       проверяет структуру списка с координатами,
       создает веременный список temp_list_coord, передоваемый
       конструктуру shapely.Polygon, проверка на корректность
       объекта shapely.Polygon
       (в случае невалидности возможны ошибки в определении
       нахождения точки).
    """

    for el in json_data['features']:
        if el['properties']['ADMIN'] == country:
            list_coord = el['geometry']['coordinates']
            break
    else:        
         #raise Exception('Страна не обнаружена!')
         #sys.exit(-1)
        return None
    temp_list_coord = []
    # структура списка координат стран типа Финляндии, России и т.д.
    if len(list_coord) > 1: 
        for i in list_coord:
            for k in i[0]:           
                temp_list_coord.append(k)
    # структура списка координат стран типа Ватикана, Австрии и т.д.
    else: # elif len(list_coord) == 1 
        temp_list_coord = list_coord[0]
    country_polygon = Polygon(temp_list_coord)
    if country_polygon.is_valid: # проверка на корректность Polygon
        return MultiPolygon([country_polygon])
    return country_polygon.buffer(0)


def transformer_coord(x, y, transformer):    
    """
       Получает на вход геометрические координаты волка и
       преобразовывает в привычные широту (lat) и долготу (lon).
    """
    lat, lon = transformer.transform(x, y) 
    return lat, lon


def create_shapely_poitns(answer_json, transform_func):
    """
        Принимает структуру json с информацией о волке,
        создает генератор, возвращающий имея волка
        и объект shapely.Point с
        центральными, преобразованными
        transformer_coord, координатами.
    """
    for i in answer_json['features']:
        name = i['properties']['yksilot'][0]['Nimi']
        lat, lon = transform_func((i['geometry']['coordinates'][0][0][0] + \
                                       i['geometry']['coordinates'][0][2][0]) // 2, \
                                     (i['geometry']['coordinates'][0][0][1] + \
                                        i['geometry']['coordinates'][0][2][1]) // 2)
        yield name, Point(lon, lat)


def check_in_area(poly, genwolfpoint):
    """
      Получает генератор с именем волка и объектом shapely.Point,
      проверяет нахождения точки (волка) в мноугольнике.
    """
    for k, v in genwolfpoint:
        yield k, v, v.within(poly)  # или - k, poly.contains(v) 


def print_wolf_in_country(wolf, coord, bool_check, country):
    """
       Печать результатов проверки
       нахождения точки (волка) в мноугольнике.
    """
    if bool_check:
        print(f'{wolf} c координатами {coord.x:.4f}\u00B0 долготы и {coord.y:.4f}\u00B0 ' +
              f'широты\n находится на территории {country}.')   
    else:
        print(f'{wolf} не обнаружен на территории {country}.') 


def get_json(url, pathfile=None):
    """
       В случае отсутствия локального json файла
       с координатами стран (> 20 мв),
       загружает по url и сохраняет в локальный файл.
       Возвращает json структуру.
    """
    if pathfile and os.path.exists(pathfile):
        with open(pathfile, 'r') as f:
            data = json.loads(f.read())
        return data
    data = requests.get(url).json()
    if pathfile:
        with open(pathfile, 'w') as f:
            json.dump(data, f)
    return data


def main():    
    countries = list(map(lambda x: x.strip(), \
                       input('Введите через запятую название стран: ').split(','))) # Finland, Russia
    transform_p = partial(transformer_coord, \
                    transformer=pyproj.Transformer.from_crs('TM35FIN(E,N)', 'WGS 84')) # инициализация
    create_polygon_p = partial(create_polygon, get_json(URLCOUNTRY, JSONFILE))
    create_shapely_poitns_p = partial(create_shapely_poitns, get_json(URLWOLF), transform_p)  
    for country in countries: 
        c_poly = create_polygon_p(country=country)
        if not c_poly:
            print(f'Координаты страны {country} не найдены!')
            continue
        check_in_area_part = partial(check_in_area, c_poly)
        print_res = partial(print_wolf_in_country, country=country)    
        for wolf, coord, check in check_in_area_part(create_shapely_poitns_p()):
            print_res(wolf, coord, check)
    
if __name__ == '__main__':
    main()



