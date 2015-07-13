import socket
import re
import json
from urlparse import parse_qs
import sqlite3 as lite
import httplib
import base64

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(('0.0.0.0', 8080))
s.listen(1)
userloged = None
uid = 0
con = lite.connect('datas.db')

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

    request_match = \
            re.match(r'^([^ ]+) ([^ ]+) ([^ ]+)\r\n(.*)$', data, re.DOTALL)
    if request_match is not None:
        method = request_match.group(1)
        resource = request_match.group(2)
        protocol = request_match.group(3)
        data = request_match.group(4)
        
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

	#linhas comentadas para previnir o uso de .notes    
    """
    try:
        with open('.notes') as note_file:
            note_dict = json.loads(note_file.read())
    except IOError:
        note_dict = dict()

    note_list = []
    for key in note_dict:
            note_list.append(note_dict[key])
    """

    try:
        with con:
            cur = con.cursor()
            cur.execute("CREATE TABLE Users(Id INTEGER PRIMARY KEY, Name TEXT UNIQUE NOT NULL, Password TEXT NOT NULL)")
            cur.execute("CREATE TABLE Notes(Id INTEGER PRIMARY KEY, Key TEXT UNIQUE NOT NULL, Note TEXT NOT NULL, CodeUser INTEGER NOT NULL, FOREIGN KEY(CodeUser)REFERENCES Users(id))")
    except lite.OperationalError:
        pass
 
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
            new_dict = parse_qs(data)
            username = new_dict['user'][0]
            password = new_dict['password'][0]
            encoded = base64.encodestring('%s:%s' % (username, password)).replace('\n', '') 
            username = str(username)
            with con:
				cur = con.cursor()
				cur.execute('SELECT Password FROM Users WHERE Name=:name',{'name': username})
				row = cur.fetchall()
				if row == None:
				    break
				authent = row[0][0]
				if encoded == authent:
					userloged = username
					cur.execute('SELECT Id from Users WHERE Name=:username',{'username':userloged})
					uid = cur.fetchone();
					#a funcao reduce realiza operacoes cumulativas em uma sequencia, da esquerda pra direita, afim de se obter um unico valor
					uid = reduce(lambda rst, d: rst * 10 + d, uid)
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
            password = new_dict['password'][0].replace('\n','').replace(';','')
            auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '') 
            new_note = []
            new_note.append(username)
            new_note.append(auth)
            try:
                with con:
                    cur = con.cursor()
                    cur.execute('INSERT INTO Users(Name,Password) VALUES(?,?)', new_note)
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
		if (userloged):
			response += 'Content-Type: text/plain; charset=utf-8\r\n'
			response += '\r\n'
			#linhas comentadas para nao mostrar os valores de .notes
			#for name in note_dict:
			#	response += '%s\n' % name
			with con:
				cur = con.cursor()
				cur.execute('SELECT Key FROM Notes where CodeUser=:id',{'id': uid})
				while True:
					rows = cur.fetchone()
					if rows == None:
						break
					for row in rows:
						response += row
						response += '\r\n'

    elif resource == '/edit_note' and userloged:
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += '\r\n'
        if method == 'GET':
            with con:
                cur = con.cursor()
                cur.execute('SELECT * FROM Notes WHERE CodeUser =:id',{'id':uid})
                while True:
					row = cur.fetchone()
					if row == None:
						break
					row = list(row)
					row = str(row)
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
			while True:
				#pode haver uma concatenacao de dados e vir dados nao suportados
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
					unsuported = True
					break

				if len(data) != int (request_headers['content-length']):
					data += conn.recv(1024)
				else:
					break

			if unsuported != True:
				new_dict = parse_qs(data)
				key_insert = new_dict['name'][0].replace('\n','').replace(';','')
				note_insert = new_dict['content'][0].replace('\n','').replace(';','')
				id_where = new_dict['line'][0].replace('\n','').replace(';','')
				with con:
					cur = con.cursor()
					#se tentar mudar uma linha que nao corresponda a este usuario, nao acontecera nada
					cur.execute('UPDATE Notes SET Key=:name, Note=:content Where Id=:line AND CodeUser=:id', {'name':key_insert, 'content':note_insert, 'line':id_where, 'id':uid})

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
					unsuported = True
					break

				if len(data) != int (request_headers['content-length']):
					data += conn.recv(1024)
				else:
					break

            if unsuported != True:
				new_dict = parse_qs(data)
				#linhas comentadas para previnir a escrita em .notes
				#note_dict[new_dict['name'][0]] = new_dict['content'][0]
				#with open('.notes', 'w') as note_file:
				#	json.dump(note_dict, note_file)
				keyins = new_dict['name'][0]
				notains = new_dict['content'][0]
				codeuserins = uid
				new_note = []
				new_note.append(keyins)
				new_note.append(notains)
				new_note.append(codeuserins)
				with con:
					cur = con.cursor()
					try: 
						cur.execute("INSERT INTO Notes(Key,Note,CodeUser) VALUES (?,?,?);", new_note)
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
            if note_match is not None:
                with con:
                    cur = con.cursor()
                    if note_match.group(1).isalpha():
                        cur.execute('SELECT Note from Notes WHERE Key=:name AND CodeUser=:uid' ,{'name': note_match.group(1), 'uid': uid})
                    else:
                        cur.execute('SELECT Note from Notes WHERE Id=:id AND CodeUser=:uid' ,{'id': (int(note_match.group(1)) + 1), 'uid': uid})
                    row = cur.fetchone()
                    response += row[0]
                        
            else:
                response += 'Para uso adequado autenticar em /auth!!!'
        except (KeyError, IndexError, TypeError):
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
    unsuported = False;
    conn.close()
