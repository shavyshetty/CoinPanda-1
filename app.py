# -*- coding: utf-8 -*-
from flask import Flask, session, render_template, json, request, redirect, url_for, escape
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
from datetime import datetime

mysql = MySQL() 
app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'panda'
app.config['MYSQL_DATABASE_PASSWORD'] = 'coinpanda'
app.config['MYSQL_DATABASE_DB'] = 'CoinPandaDB'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
mysql.init_app(app)

class ServerError(Exception):pass

@app.route('/')
def main():
    return render_template('index.html',title='CoinPanda | Home')

@app.route('/contact')
def contact():
    return render_template('ContactUs.html',title='CoinPanda | Contact Us')

@app.route('/compare')
def compare():
    if 'name' not in session:
        return redirect(url_for('login'))

    return render_template('compare.html',title='CoinPanda | Compare Currency')

@app.route('/dashboard')
def dashboard():
    if 'name' not in session:
        return redirect(url_for('login'))

    uid = session['uid']
    conn = mysql.connect()
    cur = conn.cursor()

    # Widget-1
    cur.execute("SELECT Cryptocurrency,Currency,Source,CurrentRate,Details FROM tblCurrency ORDER BY Cryptocurrency, CurrentRate ASC;")
    data1,data2,data3,data4,data5 = [],[],[],[],[]

    for row in cur.fetchall():
        obj ={'Cryptocurrency' : row[0], 'Currency' : row[1], 'Source' : row[2], 
        'CurrentRate' : row[3], 'Details': json.loads(str(row[4]))}
        data1.append(obj)

    # Widget-2,3,4
    cur.execute("""
        SELECT SUM(i.InvestmentValue) as TotalInvestment 
        , SUM(i.InvestmentVolume * c.CurrentRate) as NetWorth
        , SUM(i.InvestmentVolume * c.CurrentRate)- SUM(i.InvestmentValue) as Profit
        FROM tblInvestment i
        Inner JOIN tblCurrency c ON i.CID=c.CID
        WHERE i.UID = %s
        """, format(uid))
    data2 = cur.fetchone()

    # Widget 5
    cur.execute("""
        SELECT a.Cryptocurrency, a.InvestmentValue
        FROM tblInvestment a
        WHERE UID=%s
        """, format(uid))
    
    for row in cur.fetchall():
        data3.append(row)

    # Widget 6
    cur.execute("""
        SELECT i.Cryptocurrency, (i.InvestmentVolume * c.CurrentRate)- (i.InvestmentValue) as Profit
        FROM tblInvestment i
        INNER JOIN tblCurrency c ON i.CID=c.CID
        WHERE UID = %s and (i.InvestmentVolume * c.CurrentRate)- (i.InvestmentValue)>0
        """, format(uid))
    
    for row in cur.fetchall():
        data4.append(row)

    # Widget-7
    cur.execute("""
        SELECT c.Cryptocurrency
        , c.Symbol
        , c.Source as ExchangeName
        , i.InvestmentVolume * c.CurrentRate as TotalValue
        , i.InvestmentVolume as TotalVolume
        , i.InvestmentValue as BeforeValue
        , i.InvestmentRate as BeforeRate
        , i.InvestmentVolume * c.CurrentRate as AfterValue
        , c.CurrentRate as AfterRate
        , ((i.InvestmentVolume * c.CurrentRate)- (i.InvestmentValue)) as NetProfit
        , (((i.InvestmentVolume * c.CurrentRate)- (i.InvestmentValue))/i.InvestmentValue)*100 as NetProfitPercent
        , i.IID
        , c.Currency
        , i.InvestmentDate
        FROM tblInvestment i
        INNER JOIN tblCurrency c ON i.CID=c.CID
        WHERE UID = %s;
        """, format(uid))
    
    for row in cur.fetchall():
        data5.append(row)

    #data3 = json.dumps(data3)
    conn.close()
    return render_template('home.html',data1=data1,data2=data2,data3=data3,data4=data4,data5=data5,title='CoinPanda | My Investment Portfolio')

@app.route('/save_investment/<edit>',methods=['POST'])
def save_investment(edit):
    if 'name' not in session:
        return redirect(url_for('login')) 
    try:
        if request.method == 'POST':
            conn = mysql.connect()
            cur = conn.cursor()
            _coin = request.form['coin']
            _exchange = request.form['exchange']
            _currency = request.form['currency']
            _units = float(request.form['units'])
            _value_unit = float(request.form['value_unit'])
            _purchased_date = request.form['purchased_date']

            _curr_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # validate the received values
            if _coin and _exchange and _currency and _units and _value_unit and _purchased_date:   
                if edit == "1":
                    _invId = request.form['invId']
                    cur.execute("SELECT COUNT(1) FROM tblInvestment WHERE IID = %s;", format(_invId))

                    if not cur.fetchone()[0]:
                        conn.close()
                        return json.dumps({'error': 1, 'message' : ''})

                    cur.execute("""
                    UPDATE tblInvestment SET 
                    InvestmentValue = %s,
                    InvestmentVolume= %s,
                    InvestmentDate= %s,
                    InvestmentRate= %s,
                    UpdateDate= %s 
                    WHERE IID = %s;
                    """, 
                    ((_units*_value_unit),_units,_purchased_date,_value_unit,_curr_time,format(_invId)))

                else:
                    # Get CID
                    cur.execute("SELECT CID FROM tblCurrency WHERE (Source=%s AND Symbol=%s AND Currency = %s);", 
                    (_exchange,_coin,_currency,))
                    
                    _cid = cur.fetchone()[0]

                    if not _cid:
                        conn.close()
                        return json.dumps({'error': 1, 'message' : ''})

                    cur.execute("""
                    INSERT INTO tblInvestment(UID,CID,Cryptocurrency,Currency,InvestmentValue,
                    InvestmentVolume,InvestmentDate,InvestmentRate,InsertDate,UpdateDate) 
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
                    (session['uid'],_cid,_coin,_currency,(_units*_value_unit),_units,_purchased_date,_value_unit,
                    _curr_time,_curr_time,))
                
                conn.commit()
                conn.close()

                return json.dumps({'error': 0, 'message' : ''})
            else:
                conn.close()
                return json.dumps({'error': 2, 'message' : ''})
    except Exception as e:
        conn.close()
        return json.dumps({'error': 3, 'message' : str(e)})

    conn.close()

@app.route('/delete_investment/',methods=['POST'])
def delete_investment():
    if 'name' not in session:
        return redirect(url_for('login')) 
    try:
        if request.method == 'POST':
            conn = mysql.connect()
            cur = conn.cursor()
            
            _invId = request.form['invId']

            cur.execute("SELECT COUNT(1) FROM tblInvestment WHERE IID = %s;", format(_invId))

            if not cur.fetchone()[0]:
                conn.close()
                return json.dumps({'error': 1, 'message' : ''})

            cur.execute("DELETE FROM tblInvestment WHERE IID = %s;", format(_invId))
            conn.commit()
            conn.close()

            return json.dumps({'error': 0, 'message' : ''})
        else:
            conn.close()
            return json.dumps({'error': 2, 'message' : ''})
    except Exception as e:
        conn.close()
        return json.dumps({'error': 3, 'message' : str(e)})

    conn.close()


@app.route('/currency_specific')
def currency_specific():
    if 'name' not in session:
        return redirect(url_for('login'))

    return render_template('currency_specific.html',title='CoinPanda | Currency Specific')

@app.route('/profile')
def profile():
    if 'name' not in session:
        return redirect(url_for('login'))

    return render_template('edit.html',title='CoinPanda | Edit Profile')

@app.errorhandler(404)
def error(e):
    return render_template('404.html',title='CoinPanda | ERROR')

#   Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'name' in session:
        return redirect(url_for('dashboard'))

    error = None

    try:
        conn = mysql.connect()
        cur = conn.cursor()

        if request.method == 'POST':
            email_form  = request.form['email']
            cur.execute("SELECT COUNT(1) FROM tblUser WHERE Email = %s;", format(email_form))

            if not cur.fetchone()[0]:
                conn.close()
                return render_template('login.html', log_error=1, message='Invalid Email',title='CoinPanda | Login')

            password_form  = request.form['password']
            cur.execute("SELECT Password,FName,LName,UID FROM tblUser WHERE Email = %s;", format(email_form))

            for row in cur.fetchall():
                if check_password_hash(row[0],password_form):
                    session['email'] = request.form['email']
                    session['name'] = row[1] + " " + row[2]
                    session['uid'] = row[3]

                    conn.close()
                    return redirect(url_for('dashboard'))

            conn.close()
            return render_template('login.html', log_error =2, message='Invalid password',title='CoinPanda | Login')
    except ServerError as e:
        error = str(e)

    conn.close()
    return render_template('login.html',log_error=3,title='CoinPanda | Login')


@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('name', None)
    session.pop('uid', None)

    return redirect(url_for('login'))

@app.route('/register',methods=['POST','GET'])
def signUp():
    try:
        if request.method == 'POST':
            conn = mysql.connect()
            cur = conn.cursor()

            _fname = request.form['fName']
            _lname = request.form['lName']
            _email = request.form['Email']
            _password = request.form['Password']

            # validate the received values
            if _fname and _lname and _email and _password:
                # All Good, let's call MySQL
                _hashed_password = generate_password_hash(_password)
                cur.execute("INSERT INTO tblUser(FName,LName,Email,Password) values (%s,%s,%s,%s)", 
                (_fname,_lname, _email, _hashed_password))
                
                conn.commit()
                conn.close()

                return render_template('login.html', reg_error=0, message='Signup was successful! Please login using your credentials ...',title='CoinPanda | Sign Up')
                
            else:
                conn.close()
                return render_template('login.html', reg_error=1, message='Error! Please fill in all details!',title='CoinPanda | Sign Up')

    except Exception as e:
        conn.close()
        return render_template('login.html', reg_error = 2, message = str(e),title='CoinPanda | Sign Up')

    conn.close()
    return render_template('login.html',reg_error=3,title='CoinPanda | Sign Up')
# End login

if __name__ == "__main__":
    app.run(port=8080, host='0.0.0.0',debug=True,threaded=True)