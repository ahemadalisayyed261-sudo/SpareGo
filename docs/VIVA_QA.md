# Viva Preparation — SpareGo
**Intro (30 sec):** "Our project SpareGo digitises order and delivery of spare parts for a local auto-parts shop. We studied [shop], found that orders were on paper/WhatsApp and customers kept calling for status. Our Flask + SQLite app gives vehicle-wise part search, stock alerts, order tracking and OTP-verified delivery."

1. **Why this topic?** Real daily problem: mechanics wait for parts; shop lacks tracking. Easy field study.
2. **What did you observe?** [your real observations].
3. **What is unique?** Search by vehicle model, public tracking link, delivery OTP, rider performance report.
4. **Why OTP?** Proof of delivery; prevents disputes and wrong "delivered" marking.
5. **Order life cycle?** Placed → Packed → Out for delivery (rider needed) → Delivered (OTP needed). Cannot skip steps.
6. **How is stock protected?** Order is rejected if qty > stock; stock reduces when the order is placed.
7. **Why copy price into order_items?** So old invoices stay correct when part price changes.
8. **How does tracking work without login?** Customer enters order no. + registered phone, or opens the WhatsApp link; only status is shown, no admin data.
9. **Security?** Hashed passwords, sessions, parameterised SQL, OTP, phone check for tracking.
10. **DFD vs ERD?** DFD = flow of data between processes; ERD = tables and relationships.
11. **Normalization?** 3NF; orders and items separated; masters for parts, customers, riders.
12. **Testing?** 16 manual test cases (Appendix B), automated in `tests.py`.
13. **Limitations?** Single shop, no GPS, no online payment. **Future:** GPS, rider app, UPI link, barcode.
14. **Why Flask/SQLite?** Lightweight, free, easy for a small shop, no server setup.
15. **Your role?** [who did survey, design, coding, testing, report].

**Demo (3 min):** Login → search part by "Activa" → New Order → Mark packed → assign rider → open tracking page on phone → enter OTP → delivered → Reports → `python tests.py`.
