import base64
import os
import sqlite3
import time
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="بوابة الكرك للطلبات - Karak Gate", page_icon="🏰", layout="wide"
)


def play_auto_sound():
  sound_html = """
        <audio autoplay style="display:none;">
            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
        </audio>
    """
  components.html(sound_html, height=0, width=0)


st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none !important;}
    div[data-testid="stToolbar"] {display: none !important; visibility: hidden !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    
    .stApp { background-color: #F8F9FA; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; direction: rtl; text-align: right; }
    
    .hero-banner {
        background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(255, 102, 0, 0.3);
    }
    
    .categories-bar {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 10px 0;
        margin-bottom: 20px;
    }
    
    .cat-pill {
        background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 14px;
        white-space: nowrap;
        box-shadow: 0 3px 8px rgba(255, 102, 0, 0.3);
        text-align: center;
        display: inline-block;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# تهيئة قاعدة البيانات المحلية SQLite (اسم جديد لضمان التحديث النظيف)
# ---------------------------------------------------------
DB_PATH = "karak_gate_v2.db"


def init_db():
  conn = sqlite3.connect(DB_PATH, check_same_thread=False)
  c = conn.cursor()

  c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            rating REAL DEFAULT 4.8,
            delivery_time TEXT,
            delivery_fee TEXT,
            image_url TEXT,
            offer TEXT,
            passcode TEXT DEFAULT '5678',
            lat REAL DEFAULT 31.1852,
            lon REAL DEFAULT 35.7048,
            phone TEXT DEFAULT '0797088219'
        )
    """)

  c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            item_name TEXT,
            price REAL,
            discount TEXT,
            quantity TEXT,
            unit TEXT,
            image_url TEXT
        )
    """)

  c.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT DEFAULT '0797088219',
            vehicle TEXT,
            passcode TEXT DEFAULT '1122',
            lat REAL DEFAULT 31.1800,
            lon REAL DEFAULT 35.7000
        )
    """)

  c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            customer_name TEXT,
            phone TEXT,
            address TEXT,
            items_desc TEXT,
            payment_method TEXT,
            total_price REAL,
            status TEXT DEFAULT 'قيد المعالجة',
            cust_lat REAL DEFAULT 31.1850,
            cust_lon REAL DEFAULT 35.7050
        )
    """)

  c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
  c.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_pass', '1234')"
  )
  c.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('store_pass', '5678')"
  )
  c.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('driver_pass',"
      " '1122')"
  )

  c.execute("SELECT COUNT(*) FROM drivers")
  if c.fetchone()[0] == 0:
    c.execute(
        """INSERT INTO drivers (name, phone, vehicle, passcode) VALUES (?, ?, ?, ?)""",
        ("محمد المعايطة", "0797088219", "سيارة كيا", "1122"),
    )

  # إضافة متاجر تجريبية افتراضية في حال كانت القاعدة فارغة لضمان ظهور بيانات مباشرة
  c.execute("SELECT COUNT(*) FROM stores")
  if c.fetchone()[0] == 0:
    c.execute(
        """INSERT INTO stores (name, category, rating, delivery_time, delivery_fee, offer, image_url) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "حلويات الكرك العريقة",
            "حلويات",
            4.9,
            "15-25 دقيقة",
            "0.50 دينار",
            "خصم 10% على الكنافة",
            "",
        ),
    )
    c.execute(
        """INSERT INTO stores (name, category, rating, delivery_time, delivery_fee, offer, image_url) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "محامص القلعة",
            "محامص ومكسرات",
            4.7,
            "20-30 دقيقة",
            "0.75 دينار",
            "توصيل مجاني للطلبات فوق 10 دنانير",
            "",
        ),
    )
    conn.commit()

  conn.commit()
  return conn, c


conn, c = init_db()


def get_setting(key):
  c.execute("SELECT value FROM settings WHERE key = ?", (key,))
  row = c.fetchone()
  return row[0] if row else ""


def render_image_safely(
    img_path, width="100%", height="120px", border_radius="8px"
):
  if img_path and img_path.startswith("http"):
    return f'<img src="{img_path}" style="width:{width}; height:{height}; object-fit:cover; border-radius:{border_radius}; border:1px solid #E5E7EB; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">'
  return f'<div style="width:{width}; height:{height}; background:#E5E7EB; border-radius:{border_radius}; display:flex; align-items:center; justify-content:center; color:#6B7280; font-size:12px; text-align:center; border:1px dashed #D1D5DB;">متجر كركي</div>'


if "show_welcome" not in st.session_state:
  st.session_state["show_welcome"] = True

if "main_nav" not in st.session_state:
  st.session_state["main_nav"] = "الرئيسية"

if "cart_items" not in st.session_state:
  st.session_state["cart_items"] = []

if "cart_store" not in st.session_state:
  st.session_state["cart_store"] = ""

if st.session_state["show_welcome"]:
  st.markdown(
      """
        <style>
        .stApp { background: linear-gradient(135deg, #FF6600 0%, #FF8533 100%) !important; }
        </style>
        <div style="text-align: center; padding: 70px 20px; color: white;">
            <h1 style="font-size: 46px; font-weight: bold;">🏰 بوابة الكرك للطلبات</h1>
            <h3 style="margin-top: 15px; font-size: 20px;">منصة التوصيل والخدمات الذكية الأولى في محافظة الكرك</h3>
        </div>
    """,
      unsafe_allow_html=True,
  )
  play_auto_sound()
  time.sleep(1.2)
  st.session_state["show_welcome"] = False
  st.rerun()

st.markdown(
    """
    <div class="hero-banner">
        <h2>بوابة الكرك للطلبات - Karak Gate</h2>
        <p style="margin-top: 5px; font-size: 16px; font-weight: 600;">منصة التوصيل والخدمات الذكية الأولى في محافظة الكرك</p>
    </div>
""",
    unsafe_allow_html=True,
)

col_1, col_2, col_3, col_4, col_5 = st.columns(5)
with col_1:
  if st.button("الرئيسية", use_container_width=True):
    st.session_state["main_nav"] = "الرئيسية"
    st.rerun()
with col_2:
  if st.button("واجهة الزبائن", use_container_width=True):
    st.session_state["main_nav"] = "الزبائن"
    st.rerun()
with col_3:
  if st.button("واجهة المتاجر", use_container_width=True):
    st.session_state["main_nav"] = "المتاجر"
    st.rerun()
with col_4:
  if st.button("واجهة السائقين", use_container_width=True):
    st.session_state["main_nav"] = "السائقين"
    st.rerun()
with col_5:
  if st.button("الإدارة المركزية", use_container_width=True):
    st.session_state["main_nav"] = "الإدارة"
    st.rerun()

st.markdown("---")

if st.session_state["main_nav"] == "الرئيسية":
  st.markdown("### أقسام المنصة")
  st.markdown(
      """
        <div class="categories-bar">
            <div class="cat-pill">محامص ومكسرات</div>
            <div class="cat-pill">حلويات</div>
            <div class="cat-pill">مطاعم</div>
            <div class="cat-pill">ماركت</div>
        </div>
    """,
      unsafe_allow_html=True,
  )

  st.markdown("### المتاجر والعروض المتاحة")
  c.execute(
      "SELECT id, name, category, rating, delivery_time, delivery_fee,"
      " image_url, offer, lat, lon FROM stores"
  )
  stores_main = c.fetchall()

  if not stores_main:
    st.info("لا توجد متاجر مضافة حالياً في المنصة.")
  else:
    for store in stores_main:
      (
          s_id,
          s_name,
          s_cat,
          s_rating,
          s_time,
          s_fee,
          s_img,
          s_offer,
          s_lat,
          s_lon,
      ) = store
      col_img, col_det = st.columns([1, 5])
      with col_img:
        st.markdown(
            render_image_safely(
                s_img, width="90px", height="90px", border_radius="10px"
            ),
            unsafe_allow_html=True,
        )
      with col_det:
        st.markdown(
            f"#### {s_name}"
            " &nbsp;&nbsp;<span"
            " style='background:#FEF3C7;color:#D97706;padding:2px"
            f" 8px;border-radius:6px;font-size:14px;'>⭐ {s_rating}</span>",
            unsafe_allow_html=True,
        )
        st.write(
            f"التصنيف: {s_cat} | وقت التوصيل: {s_time} | أجور التوصيل: {s_fee}"
        )
        if s_offer:
          st.markdown(
              f"<span style='color:#FF6600; font-weight:600;'>العرض:"
              f" {s_offer}</span>",
              unsafe_allow_html=True,
          )
      st.markdown("---")

elif st.session_state["main_nav"] == "الزبائن":
  st.subheader("بوابة الزبائن وتتبع الطلبات")
  cust_t1, cust_t2, cust_t3, cust_t4 = st.tabs([
      "بياناتك وتحديد الموقع",
      "تصفح المتاجر والأصناف",
      "السلة وتفاصيل الفاتورة",
      "تتبع رحلة الطلب",
  ])

  with cust_t1:
    with st.form("cust_form_real"):
      c_name = st.text_input("الاسم الكامل:")
      c_phone = st.text_input("رقم الهاتف:", value="0797088219")
      c_address = st.text_area("العنوان بالتفصيل (مثل: الكرك، المرج...):")
      if st.form_submit_button("حفظ بياناتي وموقعي"):
        st.session_state["client_info"] = {
            "name": c_name,
            "phone": c_phone,
            "address": c_address,
        }
        st.success("تم حفظ بياناتك بنجاح!")
        st.rerun()

  with cust_t2:
    st.markdown("### المتاجر المعتمدة وأصنافها")
    c.execute(
        "SELECT id, name, category, rating, delivery_time, delivery_fee,"
        " image_url, offer FROM stores"
    )
    stores = c.fetchall()

    if not stores:
      st.info("لا توجد متاجر مضافة حالياً في المنصة.")
    else:
      for store in stores:
        (
            s_id,
            s_name,
            s_cat,
            s_rating,
            s_time,
            s_fee,
            s_img,
            s_offer,
        ) = store
        col_img, col_det = st.columns([1, 5])
        with col_img:
          st.markdown(
              render_image_safely(
                  s_img, width="80px", height="80px", border_radius="10px"
              ),
              unsafe_allow_html=True,
          )
        with col_det:
          st.markdown(
              f"#### {s_name} (التقييم: {s_rating})", unsafe_allow_html=True
          )
          st.write(
              f"التصنيف: {s_cat} | وقت التوصيل: {s_time} | التوصيل: {s_fee}"
          )
          if s_offer:
            st.markdown(
                f"<span style='color:#FF6600; font-weight:600;'>العرض:"
                f" {s_offer}</span>",
                unsafe_allow_html=True,
            )

        with st.expander(f"عرض أصناف وعروض {s_name}"):
          c.execute(
              "SELECT id, item_name, price, discount, quantity, unit, image_url"
              " FROM items WHERE TRIM(store_name) = TRIM(?)",
              (s_name,),
          )
          items = c.fetchall()
          if not items:
            st.info(f"لا توجد أصناف مضافة لهذا المتجر ({s_name}) حالياً.")
          else:
            for itm in items:
              i_id, i_name, i_price, i_disc, i_qty, i_unit, i_img = itm
              col_i_img, col_it1, col_it2 = st.columns([1, 3, 1])
              with col_i_img:
                st.markdown(
                    render_image_safely(
                        i_img, width="55px", height="55px", border_radius="8px"
                    ),
                    unsafe_allow_html=True,
                )
              with col_it1:
                st.write(
                    f"• **{i_name}**\n- السعر: **{i_price} JD**\n- العرض:"
                    f" {i_disc}\n- المتوفر: {i_qty} {i_unit}"
                )
              with col_it2:
                if st.button("إضافة للسلة", key=f"btn_add_{s_id}_{i_id}"):
                  if (
                      st.session_state["cart_store"]
                      and st.session_state["cart_store"] != s_name
                  ):
                    st.session_state["cart_items"] = []
                  st.session_state["cart_store"] = s_name
                  st.session_state["cart_items"].append({
                      "name": i_name,
                      "price": i_price,
                      "store": s_name,
                  })
                  st.success("تمت الإضافة للسلة!")
                  st.rerun()
              st.markdown("---")
        st.markdown("---")

  with cust_t3:
    st.markdown("### السلة وتفاصيل الفاتورة")
    cart_items = st.session_state.get("cart_items", [])
    cart_store = st.session_state.get("cart_store", "")

    if not cart_items:
      st.info("السلة فارغة.")
    else:
      st.write(f"المتجر الحالي: **{cart_store}**")
      subtotal = sum(item["price"] for item in cart_items)
      for c_itm in cart_items:
        st.write(f"• {c_itm['name']} — {c_itm['price']} JD")

      delivery_fee_val = 0.75
      service_fee = 0.25
      total_bill = subtotal + delivery_fee_val + service_fee

      st.markdown(
          f"""
            <div style="background:#F3F4F6; padding:15px; border-radius:10px; margin:10px 0; border: 1px solid #E5E7EB;">
                <b>تفاصيل الفاتورة:</b><br>
                • مجموع المنتجات: <b>{subtotal:.2f} JD</b><br>
                • أجور التوصيل: <b>{delivery_fee_val:.2f} JD</b><br>
                • رسوم الخدمة: <b>{service_fee:.2f} JD</b><br>
                <hr style="margin:8px 0;">
                <b>المجموع الكلي النهائي: <span style="color:#FF6600; font-size:18px;">{total_bill:.2f} JD</span></b>
            </div>
            """,
          unsafe_allow_html=True,
      )

      with st.form("payment_form_r"):
        pay_choice = st.radio(
            "طريقة الدفع:",
            ["نقداً عند الاستلام", "تحويل كليك (CliQ) - 0797088219"],
        )
        if st.form_submit_button("إرسال الطلب نهائياً"):
          client = st.session_state.get(
              "client_info",
              {
                  "name": "زبون الكرك",
                  "phone": "0797088219",
                  "address": "الكرك",
              },
          )
          items_description = ", ".join(
              [f"{i['name']} ({i['price']} JD)" for i in cart_items]
          )
          c.execute(
              """INSERT INTO orders (store_name, customer_name, phone, address, items_desc, payment_method, total_price, status) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (
                  cart_store,
                  client["name"],
                  client["phone"],
                  client["address"],
                  items_description,
                  pay_choice,
                  total_bill,
                  "قيد المعالجة",
              ),
          )
          conn.commit()
          st.success("تم إرسال الطلب بنجاح!")
          st.session_state["cart_items"] = []
          st.session_state["cart_store"] = ""
          st.rerun()

  with cust_t4:
    st.markdown("### تتبع رحلة الطلب")
    c.execute(
        "SELECT id, store_name, status, total_price, items_desc FROM orders"
    )
    for tr in c.fetchall():
      st.markdown(
          f"""
            <div style="background:white; padding:12px; border-radius:8px; border:1px solid #ddd; margin-bottom:10px;">
                <b>طلب #{tr[0]} — المتجر: {tr[1]}</b><br>
                الحالة: <span style="color:#FF6600;">{tr[2]}</span> | المبلغ: {tr[3]} JD<br>
                الطلبات: {tr[4]}
            </div>
            """,
          unsafe_allow_html=True,
      )

elif st.session_state["main_nav"] == "المتاجر":
  st.subheader("واجهة المتاجر والطلبات الواردة")
  store_pass_input = st.text_input(
      "أدخل كلمة سر لوحة المتاجر (افتراضي 5678):",
      type="password",
      key="store_login_pass",
  )
  if store_pass_input == get_setting("store_pass"):
    st.success("تم تسجيل الدخول بنجاح!")
    c.execute(
        "SELECT id, store_name, items_desc, status, total_price FROM orders"
    )
    for os_item in c.fetchall():
      st.write(
          f"طلب #{os_item[0]} | المتجر: {os_item[1]} | الطلب: {os_item[2]} |"
          f" المجموع: {os_item[4]} JD | الحالة: {os_item[3]}"
      )

elif st.session_state["main_nav"] == "السائقين":
  st.subheader("واجهة السائقين وعمليات التوصيل")
  drv_pass_input = st.text_input(
      "أدخل كلمة سر لوحة السائقين (افتراضي 1122):",
      type="password",
      key="drv_login_pass",
  )
  if drv_pass_input == get_setting("driver_pass"):
    st.success("تم تسجيل الدخول بنجاح!")
    c.execute(
        "SELECT id, store_name, customer_name, phone, address, status,"
        " total_price, items_desc FROM orders"
    )
    for do in c.fetchall():
      st.markdown(
          f"""
            <div style="background:#FFF; padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:10px;">
                <b>طلب توصيل رقم #{do[0]}</b><br>
                المتجر: {do[1]} | الزبون: {do[2]} (هاتف: {do[3]})<br>
                العنوان: {do[4]} | التفاصيل: {do[7]}<br>
                <b>المبلغ المطلوب: <span style="color:#FF6600;">{do[6]:.2f} JD</span></b> | الحالة: <b>{do[5]}</b>
            </div>
            """,
          unsafe_allow_html=True,
      )

# ---------------------------------------------------------
# الإدارة المركزية
# ---------------------------------------------------------
elif st.session_state["main_nav"] == "الإدارة":
  st.subheader("لوحة الإدارة المركزية الشاملة")
  admin_pass_input = st.text_input(
      "أدخل كلمة سر الإدارة (افتراضي 1234):",
      type="password",
      key="adm_login_pass",
  )
  if admin_pass_input == get_setting("admin_pass"):
    st.success("تم تسجيل الدخول بنجاح.")

    adm_t1, adm_t2, adm_t3, adm_t4, adm_t5, adm_t6 = st.tabs([
        "إدارة المتاجر (إضافة/تعديل/حذف)",
        "إدارة السائقين (إضافة/تعديل/حذف)",
        "إدارة الأصناف والمنتجات",
        "متابعة الطلبات",
        "التقرير المالي",
        "إعدادات النظام",
    ])

    # 1. إدارة المتاجر
    with adm_t1:
      st.markdown("### إضافة متجر جديد")
      with st.form("add_store_form_full", clear_on_submit=True):
        n_name = st.text_input("اسم المتجر الجديد:")
        n_cat = st.text_input("التصنيف (مثل: حلويات، محامص...):")
        n_time = st.text_input("وقت التوصيل:", value="20-30 دقيقة")
        n_fee = st.text_input("أجور التوصيل:", value="0.75 دينار")
        n_offer = st.text_input("العرض الخاص:")
        n_img = st.text_input("رابط صورة المتجر (URL):")
        submitted_store = st.form_submit_button("إضافة المتجر")
        if submitted_store:
          if n_name:
            c.execute(
                """INSERT INTO stores (name, category, delivery_time, delivery_fee, offer, image_url) 
                         VALUES (?, ?, ?, ?, ?, ?)""",
                (n_name, n_cat, n_time, n_fee, n_offer, n_img),
            )
            conn.commit()
            st.success(f"تمت إضافة المتجر '{n_name}' بنجاح!")
            time.sleep(0.5)
            st.rerun()
          else:
            st.warning("يرجى إدخال اسم المتجر على الأقل.")

      st.markdown("---")
      st.markdown("### قائمة المتاجر الحالية في النظام")
      c.execute("SELECT id, name, category, rating FROM stores")
      all_current_stores = c.fetchall()
      if all_current_stores:
        for st_row in all_current_stores:
          st.write(
              f"• **{st_row[1]}** | التصنيف: {st_row[2]} | التقييم: {st_row[3]}"
          )

      st.markdown("---")
      st.markdown("### تعديل أو حذف متجر قائم")
      c.execute("SELECT id, name FROM stores")
      stores_records = c.fetchall()
      if stores_records:
        store_names_map = {row[1]: row[0] for row in stores_records}
        selected_store_to_edit = st.selectbox(
            "اختر المتجر للتعديل أو الحذف:", list(store_names_map.keys())
        )
        s_id_target = store_names_map[selected_store_to_edit]

        c.execute(
            "SELECT name, category, delivery_time, delivery_fee, offer,"
            " image_url FROM stores WHERE id = ?",
            (s_id_target,),
        )
        s_data = c.fetchone()

        with st.form("edit_store_form"):
          e_name = st.text_input("اسم المتجر:", value=s_data[0])
          e_cat = st.text_input("التصنيف:", value=s_data[1])
          e_time = st.text_input("وقت التوصيل:", value=s_data[2])
          e_fee = st.text_input("أجور التوصيل:", value=s_data[3])
          e_offer = st.text_input("العرض:", value=s_data[4] or "")
          e_img = st.text_input("رابط الصورة:", value=s_data[5] or "")

          col_e1, col_e2 = st.columns(2)
          with col_e1:
            save_update = st.form_submit_button("حفظ التعديلات")
          with col_e2:
            delete_store = st.form_submit_button("حذف المتجر نهائياً")

          if save_update:
            c.execute(
                """UPDATE stores SET name = ?, category = ?, delivery_time = ?, delivery_fee = ?, offer = ?, image_url = ? WHERE id = ?""",
                (
                    e_name,
                    e_cat,
                    e_time,
                    e_fee,
                    e_offer,
                    e_img,
                    s_id_target,
                ),
            )
            conn.commit()
            st.success("تم تحديث بيانات المتجر بنجاح!")
            st.rerun()

          if delete_store:
            c.execute("DELETE FROM stores WHERE id = ?", (s_id_target,))
            conn.commit()
            st.warning(f"تم حذف المتجر '{selected_store_to_edit}' بنجاح!")
            st.rerun()

    # 2. إدارة السائقين
    with adm_t2:
      st.markdown("### إضافة سائق جديد")
      with st.form("add_driver_form", clear_on_submit=True):
        d_name = st.text_input("اسم السائق:")
        d_phone = st.text_input("رقم الهاتف:", value="0797088219")
        d_veh = st.text_input("نوع المركبة (سيارة/سكوتر):", value="سيارة")
        d_pass = st.text_input(
            "كلمة مرور السائق:", value="1122", type="password"
        )
        if st.form_submit_button("إضافة السائق"):
          if d_name:
            c.execute(
                """INSERT INTO drivers (name, phone, vehicle, passcode) VALUES (?, ?, ?, ?)""",
                (d_name, d_phone, d_veh, d_pass),
            )
            conn.commit()
            st.success(f"تمت إضافة السائق '{d_name}' بنجاح!")
            st.rerun()

      st.markdown("---")
      st.markdown("### تعديل أو حذف سائق قائم")
      c.execute("SELECT id, name FROM drivers")
      drivers_records = c.fetchall()
      if drivers_records:
        driver_map = {row[1]: row[0] for row in drivers_records}
        sel_drv_edit = st.selectbox(
            "اختر السائق للتعديل أو الحذف:", list(driver_map.keys())
        )
        d_id_target = driver_map[sel_drv_edit]

        c.execute(
            "SELECT name, phone, vehicle, passcode FROM drivers WHERE id = ?",
            (d_id_target,),
        )
        drv_data = c.fetchone()

        with st.form("edit_driver_form"):
          ed_name = st.text_input("اسم السائق:", value=drv_data[0])
          ed_phone = st.text_input("الهاتف:", value=drv_data[1])
          ed_veh = st.text_input("المركبة:", value=drv_data[2])
          ed_pass = st.text_input(
              "كلمة المرور:", value=drv_data[3], type="password"
          )

          col_d1, col_d2 = st.columns(2)
          with col_d1:
            save_drv_upd = st.form_submit_button("تحديث السائق")
          with col_d2:
            del_drv = st.form_submit_button("حذف السائق")

          if save_drv_upd:
            c.execute(
                """UPDATE drivers SET name = ?, phone = ?, vehicle = ?, passcode = ? WHERE id = ?""",
                (ed_name, ed_phone, ed_veh, ed_pass, d_id_target),
            )
            conn.commit()
            st.success("تم تحديث بيانات السائق بنجاح!")
            st.rerun()

          if del_drv:
            c.execute("DELETE FROM drivers WHERE id = ?", (d_id_target,))
            conn.commit()
            st.warning("تم حذف السائق بنجاح!")
            st.rerun()

    # 3. إدارة الأصناف
    with adm_t3:
      st.markdown("### إضافة صنف جديد للمتاجر")
      c.execute("SELECT name FROM stores")
      store_list = [row[0] for row in c.fetchall()]
      if not store_list:
        st.warning(
            "الرجاء إضافة متجر أولاً من تبويب 'إدارة المتاجر' لتتمكن من إضافة"
            " أصناف له."
        )
      else:
        with st.form("add_item_form_full", clear_on_submit=True):
          sel_store_i = st.selectbox("اختر المتجر:", store_list)
          it_name = st.text_input("اسم الصنف:")
          it_price = st.number_input(
              "السعر (بالدينار):", min_value=0.1, value=1.00
          )
          it_disc = st.text_input("الخصم أو العرض:")
          it_qty = st.text_input("الكمية المتوفرة:", value="10")
          it_unit = st.text_input("وحدة القياس:", value="كيلو")
          it_img = st.text_input("رابط صورة الصنف (URL):")

          if st.form_submit_button("حفظ الصنف"):
            if it_name:
              c.execute(
                  """INSERT INTO items (store_name, item_name, price, discount, quantity, unit, image_url) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (
                      sel_store_i,
                      it_name,
                      it_price,
                      it_disc,
                      it_qty,
                      it_unit,
                      it_img,
                  ),
              )
              conn.commit()
              st.success("تمت إضافة الصنف بنجاح!")
              st.rerun()

    # 4. متابعة الطلبات
    with adm_t4:
      st.markdown("### سجل الطلبات الكلي وتحديث حالتها")
      c.execute(
          "SELECT id, store_name, customer_name, phone, address,"
          " payment_method, total_price, status FROM orders"
      )
      all_ords = c.fetchall()
      if not all_ords:
        st.info("لا توجد طلبات مسجلة حتى الآن.")
      else:
        for ord_row in all_ords:
          st.markdown(
              f"""
                    <div style="background:white; padding:12px; border-radius:8px; border:1px solid #ddd; margin-bottom:10px;">
                        <b>طلب رقم #{ord_row[0]} — المتجر: {ord_row[1]}</b><br>
                        الزبون: {ord_row[2]} (هاتف: {ord_row[3]}) | العنوان: {ord_row[4]}<br>
                        طريقة الدفع: {ord_row[5]} | المجموع: <b>{ord_row[6]:.2f} JD</b><br>
                        الحالة الحالية: <span style="color:#FF6600;">{ord_row[7]}</span>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

    # 5. التقرير المالي
    with adm_t5:
      st.markdown("### التقرير المالي الشامل للمنصة")
      c.execute(
          "SELECT SUM(total_price), COUNT(id) FROM orders WHERE status !="
          " 'ملغي'"
      )
      res_fin = c.fetchone()
      total_sales = res_fin[0] if res_fin[0] else 0.0
      total_orders_count = res_fin[1] if res_fin[1] else 0

      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        st.metric(
            label="إجمالي المبيعات الكلية", value=f"{total_sales:.2f} JD"
        )
      with col_f2:
        st.metric(label="عدد الطلبات المنفذة", value=total_orders_count)
      with col_f3:
        st.metric(
            label="عمولة التوصيل والخدمات المتوقعة",
            value=f"{(total_orders_count * 1.00):.2f} JD",
        )

      st.markdown("---")
      st.markdown("### تفاصيل المبيعات حسب المتاجر")
      c.execute(
          "SELECT store_name, SUM(total_price), COUNT(id) FROM orders GROUP BY"
          " store_name"
      )
      store_sales = c.fetchall()
      if not store_sales:
        st.info("لا توجد بيانات مالية مسجلة بعد.")
      else:
        for s_sale in store_sales:
          st.write(
              f"• متجر **{s_sale[0]}**: عدد الطلبات ({s_sale[2]}) | إجمالي"
              f" المبيعات: **{s_sale[1]:.2f} JD**"
          )

    # 6. إعدادات النظام
    with adm_t6:
      st.markdown("### إعدادات الأمان وكلمات المرور")
      with st.form("settings_form_full"):
        new_adm_p = st.text_input("تغيير كلمة مرور الإدارة:", type="password")
        new_str_p = st.text_input("تغيير كلمة مرور المتاجر:", type="password")
        new_drv_p = st.text_input("تغيير كلمة مرور السائقين:", type="password")
        if st.form_submit_button("حفظ التعديلات"):
          if new_adm_p:
            c.execute(
                "UPDATE settings SET value = ? WHERE key = 'admin_pass'",
                (new_adm_p,),
            )
          if new_str_p:
            c.execute(
                "UPDATE settings SET value = ? WHERE key = 'store_pass'",
                (new_str_p,),
            )
          if new_drv_p:
            c.execute(
                "UPDATE settings SET value = ? WHERE key = 'driver_pass'",
                (new_drv_p,),
            )
          conn.commit()
          st.success("تم تحديث إعدادات النظام بنجاح!")
          st.rerun()