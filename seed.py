"""DEMO data (fake). Run: python seed.py. Replace with real shop data before the final demo."""
import sqlite3, app
app.init_db(); c = sqlite3.connect(app.DB)
c.executemany("INSERT INTO parts(name,brand,vehicle,price,stock,min_stock) VALUES(?,?,?,?,?,?)",
 [("Brake Pad Set","Demo Brand","Honda Activa",320,12,4),("Air Filter","Demo Brand","Maruti Swift",250,2,4),("Chain Sprocket Kit","Demo Brand","Hero Splendor",780,6,3),
  ("Clutch Plate","Demo Brand","Bajaj Pulsar 150",540,8,3),("Engine Oil 1L","Demo Brand","Universal",420,25,8),("Headlight Bulb","Demo Brand","Maruti Swift",180,3,5),("Spark Plug","Demo Brand","Honda Activa",120,30,10)])
c.executemany("INSERT INTO customers(name,phone,kind,address) VALUES(?,?,?,?)",[("Demo Garage 1","9000000011","Garage","Demo Road 1"),("Demo Mechanic 2","9000000012","Mechanic","Demo Lane 2"),("Demo Rider 3","9000000013","Individual","Demo Colony 3")])
c.executemany("INSERT INTO riders(name,phone) VALUES(?,?)",[("Demo Rider A","9100000001"),("Demo Rider B","9100000002")])
def order(cid, items, status, rid=None):
    sub = sum(p*q for _, q, p in items); fee = app.fee_for(sub)
    cur = c.execute("INSERT INTO orders(customer_id,rider_id,address,status,otp,delivery_fee,total,created_at,packed_at,out_at,delivered_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (cid, rid, "Demo address", status, "1234", fee, sub+fee, "2026-10-16 10:00", "2026-10-16 10:20" if status!="PLACED" else None, "2026-10-16 10:40" if status in("OUT_FOR_DELIVERY","DELIVERED") else None, "2026-10-16 11:10" if status=="DELIVERED" else None))
    for pid, q, p in items: c.execute("INSERT INTO order_items(order_id,part_id,qty,price) VALUES(?,?,?,?)", (cur.lastrowid, pid, q, p))
order(1, [(1,2,320),(7,4,120)], "DELIVERED", 1); order(2, [(3,1,780),(5,1,420)], "OUT_FOR_DELIVERY", 2); order(3, [(2,1,250)], "PACKED"); order(1, [(4,2,540)], "PLACED")
c.commit(); print("Demo data loaded.")
