import socket
import re
import json
from urlparse import parse_qs
import sqlite3 as lite
import httplib
import base64
#import string

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(('0.0.0.0', 8080))
s.listen(1)
loged = 0
userloged = None

while True:
    data = ''
    conn, addr = s.accept()
    print 'Connected by', addr
    while True:
        if '\r\n\r\n' in data:
            break
        new_data = conn.recv(1024)
        if not new_data:
            break
        data += new_data

	print 'DATA ORIGINAL\r\n', data
	
	print '---------------------------------------'	

    request_match = \
            re.match(r'^([^ ]+) ([^ ]+) ([^ ]+)\r\n(.*)$', data, re.DOTALL)
    if request_match is not None:
        method = request_match.group(1)
        resource = request_match.group(2)
        protocol = request_match.group(3)
        data = request_match.group(4)
	print data
        
    else:
        raise Exception('Cannot read request')
	
    request_headers = dict()

    while True:
        if data[:2] == '\r\n':
            data = data[2:]
            break
        field = re.match(r'^([^:]+): ([^\r]+)\r\n(.*)$', data, re.DOTALL)
        if field is not None:
            field_name = field.group(1)
            field_body = field.group(2)
            request_headers[field_name.lower()] = field_body
            print request_headers
            data = field.group(3)
        else:
            raise Exception('Cannot read request header')

    response = ''

    response += 'HTTP/1.1 200 OK\r\n'
    
    try:
        #print 'userloged = ', userloged
        with open('.notes') as note_file:
            note_dict = json.loads(note_file.read())
    except IOError:
        note_dict = dict()

    note_list = []
    for key in note_dict:
            note_list.append(note_dict[key])
    
    try:
        con = lite.connect('datas.db')
        with con:
            cur = con.cursor()
            cur.execute("CREATE TABLE Notes(Id INTEGER PRIMARY KEY, Key TEXT UNIQUE NOT NULL, Note TEXT NOT NULL)")
    except lite.OperationalError:
        pass
   

    try:
        con1 = lite.connect('datas.db')
        with con1:
            cur1 = con1.cursor()
            cur1.execute("CREATE TABLE Users(Id INTEGER PRIMARY KEY, Name TEXT UNIQUE NOT NULL, Password TEXT NOT NULL)")
    except lite.OperationalError:
        pass

    print loged
    print userloged
    print resource    

    if resource == '/auth':
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += '\r\n'
        if method == 'GET':
            response += """
            <html>
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                </head>
                <body>
                <form action="/auth" method="POST">
                    <h2>Insira seu usuario e senha!</h2>
                    User: <input type="text" name="user"/>
                    <br/>
                    Password: <input type="text" name="password"/>
                    <br/>
                    <input type="submit" value="Add"/>
                </form>
                </body>
            </html>
            """
        elif method == 'POST':
            print data
            new_dict = parse_qs(data)
            username = new_dict['user'][0]
            password = new_dict['password'][0]
            trying = base64.encodestring('%s:%s' % (username, password)).replace('\n', '') 
            con = lite.connect('datas.db')
            username = str(username)
            with con:
                cur = con.cursor()
                cur.execute('SELECT Password FROM Users WHERE Name=:name',{'name': username})
                row = cur.fetchall()
                if row == None:
                    break
                authent = row[0][0]
                print authent
            if trying == authent:
                loged = 1
                userloged = username
                print 'USERLOGED = ', userloged
                print loged
                response = ''
                response += 'HTTP/1.1 418 I\'m a teapot\r\n'
                response += 'Content-Type: text/html; charset=utf-8\r\n'
                response += '\r\n'
                response += """
                <html>
                    <head>
                        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                    </head>
                    <body>
                        <h1>Sucess!</h1>
                    </body>
                </html>
                """
            else:
                response = ''
                response += 'HTTP/1.1 401 Unauthorized\r\n'
                response += 'Content-Type: text/html; charset=utf-8\r\n'
                response += '\r\n'
                response += """
                <html>
                    <head>
                        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                    </head>
                    <body>
                        <h1>ERROR 401 - Unauthorized<h1>
                    </body>
                </html>
                """

    elif resource == '/register':
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += '\r\n'
        if method == 'GET':
            response += """
            <html>
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                </head>
                <body>
                <form action="register" method="POST">
                    <p>Insira seu nome e senha para registrar!</p>
                    Name: <input type="text" name="name"/>
                    <br/>
                    Password: <input type="text" name="password"/>
                    <br/>
                    <input type="submit" value="Add"/>
                </form>
                </body>
            </html>
            """
        elif method == 'POST':
            new_dict = parse_qs(data)
            username = new_dict['name'][0]
            password = new_dict['password'][0]
            auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '') 
            listtoinsert = []
            listtoinsert.append(username)
            listtoinsert.append(auth)
            con = lite.connect('datas.db')
            try:
                with con:
                    cur = con.cursor()
                    cur.execute('INSERT INTO Users(Name,Password) VALUES(?,?)', listtoinsert)
            except lite.IntegrityError:
                response = ''
                response += 'HTTP/1.1 409 Conflict\r\n'
                response += 'Content-Type: text/html; charset=utf-8\r\n'
                response += '\r\n'
                response += """
                <html>
                    <head>
                        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                    </head>
                    <body>
                        <h1>ERROR 409<h1>
                    </body>
                </html>
                """


     
    elif resource == '/notes':
        response += 'Content-Type: text/plain; charset=utf-8\r\n'
        response += '\r\n'
        for name in note_dict:
            response += '%s\n' % name
        #for count in range(0,len(note_list)):
        #    response += str(count + 1) + '\n'
        con = lite.connect('datas.db')
        with con:
            cur = con.cursor()
            cur.execute('SELECT Key FROM Notes')
            while True:
                rows = cur.fetchone()
                if rows == None:
                    break
                print rows
                for row in rows:
                    response += row
                    response += '\r\n'
	#print note_dict
	#print note_list
	#print note_list[1]    

    elif resource == '/edit_note':
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += '\r\n'
        if method == 'GET':
            con = lite.connect('datas.db')
            with con:
                cur = con.cursor()
                cur.execute('SELECT * FROM Notes;')
                #con.text_factory = str
                while True:
                    row = cur.fetchone()
                    if row == None:
                        break
                    row = list(row)
                    row = str(row)
                    print row
                    print row[0]
                    #response += row[0], row[1], row[2]
                    response += row
                    response +='\r\n'
            response += """
            <html>
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                </head>
                <body>
                <form action="edit_note" method="POST">
                    Qual linha deseja mudar: <input type="text" name="line"/>
                    <br/>
                    Name: <input type="text" name="name"/>
                    <br/>
                    Content: <input type="text" name="content"/>
                    <br/>
                    <input type="submit" value="Add"/>
                </form>
                </body>
            </html>
            """
        elif method == 'POST':
            new_dict = parse_qs(data)
            print new_dict
            rins1 = new_dict['name'][0]
            rins2 = new_dict['content'][0]
            rins3 = new_dict['line'][0]
            print rins1
            print rins2
            print rins3
            con = lite.connect('datas.db')
            with con:
                cur = con.cursor()
                cur.execute('UPDATE Notes SET Key=:name, Note=:content Where Id=:line', {'name':rins1, 'content':rins2, 'line':rins3})

    elif resource == '/add_note':
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += '\r\n'
        if method == 'GET':
            response += """
            <html>
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                </head>
                <body>
                <form action="add_note" method="POST">
                    Name: <input type="text" name="name"/>
                    <br/>
                    Content: <input type="text" name="content"/>
                    <br/>
                    <input type="submit" value="Add"/>
                </form>
                </body>
            </html>
            """
        elif method == 'POST':
            while True:
		if request_headers['content-type'] != 'application/x-www-form-urlencoded':
			response = ''
			response += 'HTTP/1.1 501 Not Implemeted\r\n'
			response += 'Content-Type: text/html; charset=utf-8\r\n'
			response += '\r\n'
			response += """
			<html>
				<head>
					<meta http-equiv="content-type" content="text/html; charset=utf-8"/>
				</head>
				<body>
					<h1>ERROR 501<h1>
				</body>
			</html>
			"""
			data = '1'
			break

		if len(data) != int (request_headers['content-length']):
			data += conn.recv(1024)
		else:
			break
	    if data != '1':
		    new_dict = parse_qs(data)
		    note_dict[new_dict['name'][0]] = new_dict['content'][0]
		    with open('.notes', 'w') as note_file:
				json.dump(note_dict, note_file)
                    
                    keyins = new_dict['name'][0]
                    notains = new_dict['content'][0]
                    listtoinsert = []
                    listtoinsert.append(keyins)
                    listtoinsert.append(notains)
                    con = lite.connect('datas.db')
                    with con:
                        cur = con.cursor()
                        try: 
                            cur.execute("INSERT INTO Notes(Key,Note) VALUES (?,?);", listtoinsert)
                        except lite.IntegrityError:
                            response = ''
                            response += 'HTTP/1.1 409 Conflict\r\n'
                            response += 'Content-Type: text/html; charset=utf-8\r\n'
                            response += '\r\n'
                            response += """
                            <html>
                                <head>
                                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                                </head>
                                <body>
                                    <h1>ERROR 409<h1>
                                </body>
                            </html>
                            """

    else:
        response += 'Content-Type: text/plain; charset=utf-8\r\n'
        response += '\r\n'
        try:
            note_match = re.match('^/notes/([a-z0-9]+)$', resource)
            #print note_match.group(1)
            if note_match is not None:
                if note_match.group(1).isalpha():
                    response += note_dict[note_match.group(1)]
                else:
                    print note_list
                    response += note_list[int(note_match.group(1))]
                    con = lite.connect('datas.db')
                    with con:
                        cur = con.cursor()
                        cur.execute('SELECT Note from Notes WHERE Id=:id',{'id': (int(note_match.group(1)) + 1)})
                        row = cur.fetchone()
                        print row
                        response += row[0]
                        
            else:
                response += 'Hello World!!!'
        except (KeyError, IndexError):
            response = ''
            response += 'HTTP/1.1 404 Not Found\r\n'
            response += 'Content-Type: text/html; charset=utf-8\r\n'
            response += '\r\n'
            response += """
            <html>
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                </head>
                <body>
                    <h1>ERROR 404<h1>
                </body>
            </html>
            """
    conn.sendall(response)

    conn.close()
