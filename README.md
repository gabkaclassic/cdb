
# cdb— минималистичный формат геоданных

Простая библиотека для работы с собственным, mmdb-подобным бинарным форматом, который хранит диапазоны IP-адресов и привязанные к ним географические данные (страна и город). 

## Установка
```bash
pip install git+https://github.com/gabkaclassic/cdb.git
```

## Возможности

- Конвертация MMDB-файла в компактный бинарный формат
- Быстрый поиск по IP
- Объединение нескольких `.cdb` файлов
- Чтение и запись собственного формата
- Простой и лёгкий формат

## Пример использования

### Конвертация MMDB → CDB


```python
from cdb import mmdb_file_to_cdb

mmdb_file_to_cdb("GeoLite2-City.mmdb", "data.cdb")
```
### Чтение и поиск по IP
```python
from cdb import read_cdb, search_geo

ips, mapping = read_cdb("data.cdb")
search_geo(ips, "8.8.8.8", mapping)
```
### Объединение нескольких .cdb файлов

```python
from cdb import merge_cdbs, merge_cdbs_and_save

ips, mapping = merge_cdbs("data1.cdb", "data2.cdb")

merge_cdbs_and_save("collapsed.cdb", "data1.cdb", "data2.cdb")
```
### Ручная сериализация и десериализация
```python
from cdb import serialize, deserialize

# serialize → bytes
data = serialize(ips, mapping)

# deserialize ← bytes
triples, map_back = deserialize(data)

```
### Конвертация ip/сети в int (CIDR → диапазон)

```python
from cdb import cidr_to_int

ip = cidr_to_int("192.168.0.2")

ip_from, ip_to = cidr_to_int("192.168.0.0/24", with_broadcast=False)
```
### Ручная запись/чтение .cdb файла

```python
from cdb import write_cdb, read_cdb

write_cdb(networks, mapping, "output.cdb")

networks, mapping = read_cdb("output.cdb")
```