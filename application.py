from flask import *
import datetime
import hashlib
import pyodbc
import json
from my_server_setting import server, database, username, password, driver 
app = Flask(__name__)

# 入浴時間リスト
times = []
times.append(datetime.datetime.strptime('17:00', "%H:%M"))
while times[-1] < datetime.datetime.strptime('22:50', "%H:%M"):
    times.append(times[-1] + datetime.timedelta(minutes=25))
i=0
while i < len(times):
    times[i] = times[i].strftime("%H:%M")
    i += 1

@app.route("/", methods=["GET", "POST"])
def hello():
    return render_template("index.html", Error=0)

@app.route("/reserve", methods=["GET", "POST"])
def login_manager():
    # ユーザ変数取得
    print(request)
    userid = request.form["userid"]
    userpassword = request.form["password"]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()
    # DBからパスワード取得
    cursor.execute("SELECT userpassword FROM users WHERE userid='" + userid + "'")
    result = cursor.fetchone()
    # パスワード認証
    i = 0
    while i<10:
        userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
        i += 1
    if userid is "" or userpassword is "":
        return render_template("index.html", Error=1)
    elif result[0] != userpassword:
        return render_template("index.html", Error=2)
    # DBから予約状況取得
    now = datetime.datetime.now()
    today = now.strftime("%Y_%m_%d ")
    sql = "SELECT "
    i = 0
    while i < len(times)-1:
        sql = sql + "SUM(CASE WHEN date = '" + today + times[i] + "' THEN 1 ELSE 0 END), "
        i += 1
    sql_small = sql[:-2] +" FROM reserve WHERE bath_type = 0"
    sql_large = sql[:-2] +" FROM reserve WHERE bath_type = 1"
    cursor.execute(sql_small)
    reservation_small = cursor.fetchone()
    cursor.execute(sql_large)
    reservation_large = cursor.fetchone()
    print(reservation_small)
    print(reservation_large)
    # 既存の自身の予約を確認
    sql = "SELECT bath_type, date FROM reserve WHERE userid='" + userid +"' AND date LIKE '" + today + "%'"
    cursor.execute(sql)
    result = cursor.fetchone()
    if result[0] == "":
        pass
    else:
        
    # DB切断
    cursor.close()
    cnxn.close()
    # 返却処理
    dic = {'userid':userid, 'login_flag':True}
    responce = make_response(render_template("reserve.html",today=now.strftime("%m/%d") ,userid=userid, times=times, times_len=len(times), reservation_small=reservation_small, reservation_large=reservation_large))
    responce.set_cookie('cookie', value = json.dumps(dic))
    return responce

@app.route("/reserve_resister", methods=["GET", "POST"])
def reserve_register():
    # ユーザ変数取得
    cookie = request.cookies.get('cookie', None)
    dic = json.loads(cookie)
    print(request)
    desired_time = request.form["desired_time"]
    now = datetime.datetime.now()
    bath_type = int(desired_time)/100
    desired_time = now.strftime("%Y_%m_%d ") + times[int(desired_time)%100]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    # パスワード認証
    i = 0
    while i<10:
        userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
        i += cursor = cnxn.cursor()
    # DBに予約登録
    sql = "INSERT INTO reserve VALUES('" + dic["userid"] + "', " + str(bath_type) + ", '" + desired_time + "')"
    cursor.execute(sql)
    cnxn.commit()
    # DB切断
    cursor.close()
    cnxn.close()
    #返却処理
    return render_template("reserve_success.html", desired_time=desired_time, userid=dic["userid"])
    
@app.route("/user_resist_form", methods=["GET", "POST"])
def user_regist_form():
    return render_template("user_regist_form.html")

@app.route("/user_resister", methods=["GET","POST"])
def user_resister():
    # ユーザ変数取得
    userid = request.form["userid"]
    userpassword = request.form["userpassword"]
    # DB接続
    cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password)
    cursor = cnxn.cursor()
    # DBに学籍番号の存在を問い合わせ
    sql = "SELECT username FROM users WHERE userid='" + userid + "'"
    cursor.execute(sql)
    result = cursor.fetchone()
    if(result[0] == ""):
        return render_template("user_resist_form.html", Error=1)
    # DBにパスワードがすでに登録されているかを確認
    sql = "SELECT userpassword FROM users WHERE userid='" + userid + "'"
    cursor.execute(sql)
    result = cursor.fetchone()
    if(result[0] != ""):
        return render_template("user_resist_form.html", Error=2)
    # パスワードストレッチング
    i = 0
    while i<10:
        userpassword = hashlib.sha256(userpassword.encode()).hexdigest()
        i += 1
    # DBにパスワードを登録
    sql = "UPDATE users SET userpassword='" + userpassword + "' WHERE userid='" + userid + "')"
    cursor.execute(sql)
    cnxn.commit()
    # DB切断
    cursor.close()
    cnxn.close()
    # 返却処理
    return render_template("user_resist_success.html")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)