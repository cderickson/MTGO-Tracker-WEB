from flask import render_template, request, Blueprint, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime
from .models import User, Match, Game, Play, Pick, Draft
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
import time
import modo
import pickle
import math 

page_size = 25

views = Blueprint('views', __name__)

@views.route('/')
def index():
	return render_template('index.html', user=current_user)

@views.route('/register')
def register():
	inputs = ['', '', '', '']
	return render_template('register.html', user=current_user, inputs=inputs)

@views.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		login_email = request.form.get('login_email')
		login_pwd = request.form.get('login_pwd')
		user = User.query.filter_by(email=login_email).first()
		if user:
			if check_password_hash(user.pwd, login_pwd):
				login_user(user, remember=True)
				return render_template('index.html', user=current_user, success_message='Logged in.')
			else:
				return render_template('login.html', user=current_user, error_message='Email/Password combination not found.')
		else:
			return render_template('login.html', user=current_user, error_message='Email not found.')

	return render_template('login.html', user=current_user)

@views.route('/logout')
@login_required
def logout():
	logout_user()
	return render_template('login.html', user=current_user)

@views.route('/form', methods=['POST'])
def form():
	inputs = [request.form.get('email'), request.form.get('pwd'), request.form.get('pwd_confirm'), request.form.get('hero')]

	if (not inputs[0]) or (not inputs[1]) or (not inputs[2]) or (not inputs[3]):
		error_message = 'Please fill in all fields.'
		return render_template('register.html', user=current_user, error_message=error_message, inputs=inputs)
	elif inputs[1] != inputs[2]:
		error_message = 'Passwords do not match.'
		return render_template('register.html', user=current_user, error_message=error_message, inputs=inputs)
	else:
		new_user = User(email=inputs[0], pwd=generate_password_hash(inputs[1], method='sha256'), username=inputs[3])
		db.session.add(new_user)
		db.session.commit()
		success_message = 'New user created.'
		login_user(new_user, remember=True)
		return render_template('index.html', user=current_user, success_message=success_message)

	return render_template('form.html', user=current_user, inputs=inputs)

@views.route('/test', methods=['GET', 'POST'])
def test():
	table = Match.query.filter_by(user_id=current_user.id).order_by(Match.date).limit(25).all()
	return render_template('test.html', user=current_user, table_name='matches', table=table)

@views.route('/load_drafts', methods=['POST'])
def load_drafts():
	for (root,dirs,files) in os.walk('C:\\Users\\chris\\Documents\\GitHub\\MTGO-Tracker\\draftlogs'):
		break
	for i in files:
		if (i.count(".") != 3) or (i.count("-") != 4) or (".txt" not in i):
			pass
		# elif (i in PARSED_DRAFT_DICT):
		#     os.chdir(root)
		else:
			os.chdir(root)
			with io.open(i,"r",encoding="ansi") as gamelog:
				initial = gamelog.read()
			try:
				parsed_data = modo.parse_draft_log(i,initial)
				print(f'Parsed DraftLog: {i}')
			except Exception as error:
				#print(f'Error while parsing DraftLog: {i}: {error.message}')
				continue
			# if parsed_data[0][0][0] in SKIP_DRAFTS:
			#     #print(f'Skipped DraftLog (in SKIP_DRAFTS): {i}')
			#     continue

			for draft in parsed_data[0]:
				new_draft = Draft(user_id=current_user.id,
								  draft_id=draft[0],
								  hero=draft[1],
								  player2=draft[2],
								  player3=draft[3],
								  player4=draft[4],
								  player5=draft[5],
								  player6=draft[6],
								  player7=draft[7],
								  player8=draft[8],
								  match_wins=draft[9],
								  match_losses=draft[10],
								  format=draft[11],
								  date=draft[12])
				if Draft.query.filter_by(draft_id=draft[0], hero=draft[1]).first():
					pass
				else:
					db.session.add(new_draft)
					db.session.commit()

			for pick in parsed_data[1]:
				new_pick = Pick(user_id=current_user.id,
								draft_id=pick[0],
								card=pick[1],
								pack_num=pick[2],
								pick_num=pick[3],
								pick_ovr=pick[4],
								avail1=pick[5],
								avail2=pick[6],
								avail3=pick[7],
								avail4=pick[8],
								avail5=pick[9],
								avail6=pick[10],
								avail7=pick[11],
								avail8=pick[12],
								avail9=pick[13],
								avail10=pick[14],
								avail11=pick[15],
								avail12=pick[16],
								avail13=pick[17],
								avail14=pick[18])
				if Pick.query.filter_by(user_id=current_user.id, draft_id=pick[0], pick_ovr=pick[4]).first():
					pass
				else:
					db.session.add(new_pick)
					db.session.commit()
			#DRAFTS_TABLE.extend(parsed_data[0])
			#PICKS_TABLE.extend(parsed_data[1])
			

			#PARSED_DRAFT_DICT[i] = parsed_data[2]

	table = Draft.query.filter_by(user_id=current_user.id).order_by(Draft.date).limit(25).all()
	return render_template('test.html', user=current_user, table_name='drafts', table=table, success_message=f'Uploaded Drafts, Picks.')

@views.route('/load', methods=['POST'])
def load():
	new_data = [[],[],[],{}]
	for (root,dirs,files) in os.walk('C:\\Users\\chris\\Documents\\GitHub\\MTGO-Tracker\\gamelogs'):
		for i in files:
			if ("Match_GameLog_" not in i) or (len(i) < 30):
				pass
			else:
				os.chdir(root)
				with io.open(i,"r",encoding="ansi") as gamelog:
					initial = gamelog.read()
					mtime = time.ctime(os.path.getmtime(i))
				try:
					parsed_data = modo.get_all_data(initial,mtime)
					parsed_data_inverted = modo.invert_join([[parsed_data[0]], parsed_data[1], parsed_data[2], parsed_data[3], parsed_data[4]])
					#print('Parsed GameLog: ' + i + '\n')
				except Exception as error:
					#print('Error while parsing GameLog: ' + i + '\n')
					continue

				# if parsed_data[0][0] in SKIP_FILES:
				# 	print('Skipped GameLog (in SKIP_FILES): ' + i + '\n')
				# 	continue
				# if isinstance(parsed_data, str):
				# 	skip_dict[i] = parsed_data
				# 	continue
				# PARSED_FILE_DICT[i] = (parsed_data[0][0],datetime.datetime.strptime(mtime,"%a %b %d %H:%M:%S %Y"))
				
				for match in parsed_data_inverted[0]:
					new_match = Match(user_id=current_user.id,
									  match_id=match[0],
									  draft_id=match[1],
									  p1=match[2],
									  p1_arch=match[3],
									  p1_subarch=match[4],
									  p2=match[5],
									  p2_arch=match[6],
									  p2_subarch=match[7],
									  p1_roll=match[8],
									  p2_roll=match[9],
									  roll_winner=match[10],
									  p1_wins=match[11],
									  p2_wins=match[12],
									  match_winner=match[13],
									  format=match[14],
									  limited_format=match[15],
									  match_type=match[16],
									  date=match[17])

					if Match.query.filter_by(match_id=match[0], p1=match[2]).first():
						pass
					else:
						db.session.add(new_match)
						db.session.commit()

				for game in parsed_data_inverted[1]:
					new_game = Game(user_id=current_user.id,
									match_id=game[0],
									p1=game[1],
									p2=game[2],
									game_num=game[3],
									pd_selector=game[4],
									pd_choice=game[5],
									on_play=game[6],
									on_draw=game[7],
									p1_mulls=game[8],
									p2_mulls=game[9],
									turns=game[10],
									game_winner=game[11])
					if Game.query.filter_by(match_id=game[0], game_num=game[3], p1=game[1]).first():
						pass
					else:
						db.session.add(new_game)
						db.session.commit()

				for play in parsed_data_inverted[2]:
					new_play = Play(user_id=current_user.id,
									match_id=play[0],
									game_num=play[1],
									play_num=play[2],
									turn_num=play[3],
									casting_player=play[4],
									action=play[5],
									primary_card=play[6],
									target1=play[7],
									target2=play[8],
									target3=play[9],
									opp_target=play[10],
									self_target=play[11],
									cards_drawn=play[12],
									attackers=play[13],
									active_player=play[14],
									non_active_player=play[15])
					if Play.query.filter_by(match_id=play[0], game_num=play[1], play_num=play[2]).first():
						pass
					else:
						db.session.add(new_play)
						db.session.commit()
				
				new_data[0].append(parsed_data[0])
				for i in parsed_data[1]:
					new_data[1].append(i)
				for i in parsed_data[2]:
					new_data[2].append(i)
				for i in parsed_data[3]:
					new_data[3] = new_data[3] | parsed_data[3]

				# if parsed_data[4][0] == True:
				# 	TIMEOUT[parsed_data[0][0]] = parsed_data[4][1]
		new_data_inverted = modo.invert_join(new_data)
	
	table = Match.query.filter_by(user_id=current_user.id).order_by(Match.date).limit(25).all()
	return render_template('test.html', user=current_user, table_name='matches', table=table, success_message='Uploaded Data.')

@views.route('/table/<table_name>/<page_num>')
def table(table_name, page_num):
	if table_name.lower() == 'matches':
		pages = math.ceil(Match.query.filter_by(user_id=current_user.id).count()/page_size)
		if (int(page_num) < 1) or (int(page_num) > pages):
			page_num = 0
		table = Match.query.filter_by(user_id=current_user.id).order_by(Match.match_id).limit(page_size*int(page_num)).all()
		#table = Match.query.filter_by(user_id=current_user.id, p1=current_user.username).order_by(Match.match_id).limit(page_size*int(page_num)).all()
	elif table_name.lower() == 'games':
		pages = math.ceil(Game.query.filter_by(user_id=current_user.id).count()/page_size)
		if (int(page_num) < 1) or (int(page_num) > pages):
			page_num = 0
		table = Game.query.filter_by(user_id=current_user.id, p1=current_user.username).order_by(Game.match_id).limit(page_size*int(page_num)).all()
	elif table_name.lower() == 'plays':
		pages = math.ceil(Play.query.filter_by(user_id=current_user.id).count()/page_size)
		if (int(page_num) < 1) or (int(page_num) > pages):
			page_num = 0
		table = Play.query.filter_by(user_id=current_user.id).order_by(Play.match_id).limit(page_size*int(page_num)).all()
	elif table_name.lower() == 'drafts':
		pages = math.ceil(Draft.query.filter_by(user_id=current_user.id).count()/page_size)
		if (int(page_num) < 1) or (int(page_num) > pages):
			page_num = 0
		table = Draft.query.filter_by(user_id=current_user.id).order_by(Draft.draft_id).limit(page_size*int(page_num)).all()
	elif table_name.lower() == 'picks':
		pages = math.ceil(Pick.query.filter_by(user_id=current_user.id).count()/page_size)
		if (int(page_num) < 1) or (int(page_num) > pages):
			page_num = 0
		table = Pick.query.filter_by(user_id=current_user.id).order_by(Pick.draft_id).limit(page_size*int(page_num)).all()

	if pages == int(page_num):
		table = table[(int(page_num)-1)*page_size:]
	else:
		table = table[-page_size:]
	return render_template('test.html', user=current_user, table_name=table_name, table=table, page_num=page_num, pages=pages)

@views.route('/table/<table_name>/<match_id>/<game_num>')
def table_drill(table_name, match_id, game_num):
	if table_name.lower() == 'games':
		table = Game.query.filter_by(user_id=current_user.id, match_id=match_id, p1=current_user.username).order_by(Game.match_id).all() 
	elif table_name.lower() == 'plays':
		table = Play.query.filter_by(user_id=current_user.id, match_id=match_id, game_num=game_num).order_by(Play.match_id).all()  

	return render_template('test.html', user=current_user, table_name=table_name, table=table)

@views.route('/table/<table_name>/<draft_id>/0')
def draft_drill(table_name, draft_id):
	if table_name.lower() == 'picks':
		table = Pick.query.filter_by(user_id=current_user.id, draft_id=draft_id).order_by(Pick.pick_ovr).all()  

	return render_template('test.html', user=current_user, table_name=table_name, table=table)

@views.route('/revise', methods=['POST'])
def revise():
	match_id = request.form.get('Match_ID')
	p1_arch = request.form.get('P1Arch')
	p1_subarch = request.form.get('P1_Subarch')
	p2_arch = request.form.get('P2Arch')
	p2_subarch = request.form.get('P2_Subarch')
	fmt = request.form.get('Format')
	limited_format = request.form.get('Limited_Format')
	match_type = request.form.get('Match_Type')
	page_num = request.form.get('Page_Num')

	matches = Match.query.filter_by(match_id=match_id).all()
	for match in matches:
		if match.p1 == current_user.username:
			match.p1_arch = p1_arch
			match.p1_subarch = p1_subarch
			match.p2_arch = p2_arch
			match.p2_subarch = p2_subarch
		else:
			match.p1_arch = p2_arch 
			match.p1_subarch = p2_subarch 
			match.p2_arch = p1_arch
			match.p2_subarch = p1_subarch
		match.format = fmt 
		match.limited_format = limited_format
		match.match_type = match_type

	pages = math.ceil(Match.query.filter_by(user_id=current_user.id).count()/page_size)
	table = Match.query.filter_by(user_id=current_user.id).order_by(Match.match_id).limit(page_size*int(page_num)).all()
	#table = Match.query.filter_by(user_id=current_user.id, p1=current_user.username).order_by(Match.match_id).limit(page_size*int(page_num)).all()
	if pages == int(page_num):
		table = table[(int(page_num)-1)*page_size:]
	else:
		table = table[-page_size:]

	try:
		db.session.commit()
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages, success_message="Record Updated.")
	except:
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages, error_message="Error Updating Record.")

@views.route('/revise_multi', methods=['POST'])
def revise_multi():
	match_id_str = request.form.get('Match_ID_Multi')
	field_to_change = request.form.get('FieldToChangeMulti')
	p1_arch = request.form.get('P1ArchMulti')
	p1_subarch = request.form.get('P1_Subarch_Multi')
	p2_arch = request.form.get('P2ArchMulti')
	p2_subarch = request.form.get('P2_Subarch_Multi')
	fmt = request.form.get('FormatMulti')
	limited_format = request.form.get('Limited_FormatMulti')
	match_type = request.form.get('Match_TypeMulti')
	page_num = request.form.get('Page_Num_Multi')

	match_ids = match_id_str.split(',')

	matches = Match.query.filter(Match.match_id.in_(match_ids)).all()
	for match in matches:
		if field_to_change == 'P1 Deck':
			if match.p1 == current_user.username:
				match.p1_arch = p1_arch
				match.p1_subarch = p1_subarch
			else:
				match.p2_arch = p1_arch 
				match.p2_subarch = p1_subarch 
		elif field_to_change == 'P2 Deck':
			if match.p1 == current_user.username:
				match.p2_arch = p2_arch
				match.p2_subarch = p2_subarch
			else:
				match.p1_arch = p2_arch 
				match.p1_subarch = p2_subarch
		elif field_to_change == 'Format':
			match.format = fmt 
			match.limited_format = limited_format
		elif field_to_change == 'Match Type':
			match.match_type = match_type

	pages = math.ceil(Match.query.filter_by(user_id=current_user.id).count()/page_size)
	table = Match.query.filter_by(user_id=current_user.id).order_by(Match.match_id).limit(page_size*int(page_num)).all()
	#table = Match.query.filter_by(user_id=current_user.id, p1=current_user.username).order_by(Match.match_id).limit(page_size*int(page_num)).all()
	if pages == int(page_num):
		table = table[(int(page_num)-1)*page_size:]
	else:
		table = table[-page_size:]

	try:
		db.session.commit()
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages, success_message="Record Updated.")
	except:
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages, error_message="Error Updating Record.")

@views.route('/values/<match_id>')
def values(match_id):
	match = Match.query.filter_by(match_id=match_id, user_id=current_user.id, p1=current_user.username).first()
	return match.as_dict()

@views.route('/test2/<row>')
def test2(row):
	return render_template('index.html', user=current_user, success_message=row)