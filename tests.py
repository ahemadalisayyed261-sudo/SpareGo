"""Automated versions of the manual test cases. Run: python tests.py"""
import os, tempfile, sqlite3, app
app.DB = os.path.join(tempfile.mkdtemp(), "t.db"); app.init_db(); app.app.config["TESTING"] = True
c = app.app.test_client(); R = []
q = lambda s: sqlite3.connect(app.DB).execute(s).fetchone()[0]
def t(i, n, ok): R.append(ok); print(f"{i}  {'PASS' if ok else 'FAIL'}  {n}")
t("TC01","Wrong password rejected", b"Wrong username" in c.post("/login",data={"username":"admin","password":"x"},follow_redirects=True).data)
t("TC02","Valid login opens dashboard", b"Dashboard" in c.post("/login",data={"username":"admin","password":"admin123"},follow_redirects=True).data)
c.post("/parts",data={"name":"Brake Pad","brand":"B","vehicle":"Activa","price":"300","stock":"10","min_stock":"3"})
t("TC03","Add part", q("select count(*) from parts")==1)
c.post("/customers",data={"name":"Bad","phone":"123","kind":"Individual","address":""}); c.post("/customers",data={"name":"Garage X","phone":"9876543210","kind":"Garage","address":"A"})
t("TC04","Invalid phone rejected, valid customer saved", q("select count(*) from customers")==1)
c.post("/riders",data={"name":"Rider 1","phone":"9"}); t("TC05","Add rider", q("select count(*) from riders")==1)
c.post("/order/new",data={"customer_id":"1","address":"Addr","part_id":["1","",""],"qty":["20","",""]}); t("TC06","Order above stock rejected", q("select count(*) from orders")==0)
c.post("/order/new",data={"customer_id":"1","address":"Addr","part_id":["1","",""],"qty":["2","",""]})
t("TC07","Order placed: total 600+40 fee, stock 10->8", q("select total from orders")==640 and q("select stock from parts")==8)
t("TC08","Free delivery at Rs 1000+", app.fee_for(1000)==0 and app.fee_for(999)==40)
c.post("/order/1/advance"); t("TC09","Placed -> Packed", q("select status from orders")=="PACKED")
c.post("/order/1/advance"); t("TC10","Cannot dispatch without rider", q("select status from orders")=="PACKED")
c.post("/order/1/advance",data={"rider_id":"1"}); t("TC11","Assign rider -> Out for delivery", q("select status from orders")=="OUT_FOR_DELIVERY")
c.post("/order/1/advance",data={"otp":"0000"}); t("TC12","Wrong OTP does not deliver", q("select status from orders")=="OUT_FOR_DELIVERY")
c.post("/order/1/advance",data={"otp":q("select otp from orders")}); t("TC13","Correct OTP -> Delivered", q("select status from orders")=="DELIVERED")
pub = app.app.test_client()
t("TC14","Public tracking works without login", b"Delivered" in pub.get("/track/1").data)
t("TC15","Tracking lookup rejects wrong phone", b"not found" in pub.post("/track",data={"oid":"1","phone":"1111111111"},follow_redirects=True).data)
t("TC16","Admin pages need login", pub.get("/orders").status_code==302)
print(f"\n{sum(R)}/{len(R)} passed"); raise SystemExit(0 if all(R) else 1)
