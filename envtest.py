import pyTigerGraph as tg

conn = tg.TigerGraphConnection(
    host='https://tg-17b98dc4-8656-4f8d-bc0a-d30e8fdd5b27.tg-3452941248.i.tgcloud.io',
    graphname="TigerGraph",
    username="dhruvpandey1476@gmail.com",
    password="Dhruv1476",
    tgCloud=True,
)
print(conn.echo())