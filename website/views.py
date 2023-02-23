from flask import render_template, request, Blueprint, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, create_engine, desc, select
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime
from .models import User, Match, Game, Play, Pick, Draft, GameActions, Removed
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
import time
import modo
import pickle
import math 
import pandas as pd

page_size = 25

def get_input_options():
	in_header = False
	in_instr = True
	input_options = {}
	x = ""
	y = []
	with io.open("INPUT_OPTIONS.txt","r",encoding="ansi") as file:
		initial = file.read().split("\n")
		for i in initial:
			if i == "-----------------------------":
				if in_instr:
					in_instr = False
				in_header = not in_header
				if in_header == False:
					x = last.split(":")[0].split("# ")[1]
				elif x != "":
					input_options[x] = y
					y = []                        
			elif (in_header == False) and (i != "") and (in_instr == False):
				y.append(i)
			last = i
	return input_options
def get_multifaced_cards():
	multifaced_cards = {}
	with io.open("MULTIFACED_CARDS.txt","r",encoding="ansi") as file:
		initial = file.read().split("\n")
		for i in initial:
			if i.isupper():
				multifaced_cards[i] = {}
				last = i
			if ' // ' in i:
				multifaced_cards[last][i.split(' // ')[0]] = i.split(' // ')[1]
	return multifaced_cards
def get_all_decks():
	for file in os.listdir(os.getcwd()):
		if file.startswith('ALL_DECKS'):
			return pickle.load(open(file,'rb'))

options = get_input_options()
multifaced = get_multifaced_cards()
all_decks = get_all_decks()

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
				flash('Logged in.', category='success')
				return redirect("/")
			else:
				flash('Email/Password combination not found.', category='error')
				return render_template('login.html', user=current_user)
		else:
			flash('Email not found.', category='error')
			return render_template('login.html', user=current_user)

	return render_template('login.html', user=current_user)

@views.route('/logout')
@login_required
def logout():
	logout_user()
	flash('User logged out.', category='error')
	return redirect("/")

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
		return render_template('index.html', user=current_user)

	return render_template('form.html', user=current_user, inputs=inputs)

@views.route('/load', methods=['POST'])
def load():
	dataToImport = request.form.get('dataToImport')
	root_folder = os.getcwd()

	if dataToImport == 'Matches':
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

					if Removed.query.filter_by(match_id=parsed_data_inverted[0][0][0]).first():
						print("skipped:"+match[0][0][0])
						continue

					# if isinstance(parsed_data, str):
					# 	skip_dict[i] = parsed_data
					# 	continue
					# PARSED_FILE_DICT[i] = (parsed_data[0][0],datetime.datetime.strptime(mtime,"%a %b %d %H:%M:%S %Y"))
					
					for match in parsed_data_inverted[0]:
						if Match.query.filter_by(match_id=match[0], p1=match[2]).first():
							continue
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
						db.session.add(new_match)
						db.session.commit()

					for game in parsed_data_inverted[1]:
						if Game.query.filter_by(match_id=game[0], game_num=game[3], p1=game[1]).first():
							continue
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
						db.session.add(new_game)
						db.session.commit()

					for play in parsed_data_inverted[2]:
						if Play.query.filter_by(match_id=play[0], game_num=play[1], play_num=play[2]).first():
							continue
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
						db.session.add(new_play)
						db.session.commit()

					for na_game in parsed_data_inverted[3]:
						if GameActions.query.filter_by(user_id=current_user.id, match_id=na_game[:-2], game_num=na_game[-1]).first():
							continue
						ga15_string = ''
						for index,i in enumerate(parsed_data_inverted[3][na_game]):
							ga15_string += i
							if index != len(parsed_data_inverted[3][na_game])-1:
								ga15_string += '\n'
						new_ga15 = GameActions(user_id=current_user.id,
											   match_id=na_game[:-2],
											   game_num=na_game[-1],
											   game_actions=ga15_string)
						db.session.add(new_ga15)
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
		
		os.chdir(root_folder)
		return redirect("/table/matches/1")

	if dataToImport == 'Drafts':
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
					if Draft.query.filter_by(draft_id=draft[0], hero=draft[1]).first():
						continue
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
					db.session.add(new_draft)
					db.session.commit()

				for pick in parsed_data[1]:
					if Pick.query.filter_by(user_id=current_user.id, draft_id=pick[0], pick_ovr=pick[4]).first():
						continue
					p = pick
					for index,i in enumerate(p):
						if i == 'NA':
							p[index] = ''
					new_pick = Pick(user_id=current_user.id,
									draft_id=pick[0],
									card=pick[1],
									pack_num=pick[2],
									pick_num=pick[3],
									pick_ovr=pick[4],
									avail1=p[5],
									avail2=p[6],
									avail3=p[7],
									avail4=p[8],
									avail5=p[9],
									avail6=p[10],
									avail7=p[11],
									avail8=p[12],
									avail9=p[13],
									avail10=p[14],
									avail11=p[15],
									avail12=p[16],
									avail13=p[17],
									avail14=p[18])
					db.session.add(new_pick)
					db.session.commit()

		os.chdir(root_folder)
		return redirect("/table/drafts/1")

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

@views.route('/table/<table_name>/<row_id>/<game_num>')
def table_drill(table_name, row_id, game_num):
	if table_name.lower() == 'games':
		table = Game.query.filter_by(user_id=current_user.id, match_id=row_id, p1=current_user.username).order_by(Game.match_id).all() 
	elif table_name.lower() == 'plays':
		table = Play.query.filter_by(user_id=current_user.id, match_id=row_id, game_num=game_num).order_by(Play.match_id).all()  
	elif table_name.lower() == 'picks':
		table = Pick.query.filter_by(user_id=current_user.id, draft_id=row_id).order_by(Pick.pick_ovr).all()  

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
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages)
	except:
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages)

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
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages)
	except:
		return render_template('test.html', user=current_user, table_name="matches", table=table, page_num=page_num, pages=pages)

@views.route('/values/<match_id>')
def values(match_id):
	match = Match.query.filter_by(match_id=match_id, user_id=current_user.id, p1=current_user.username).first()
	return match.as_dict()

@views.route('/game_winner/<match_id>/<game_num>/<game_winner>')
def game_winner(match_id, game_num, game_winner):
	if game_winner != '0':
		games = Game.query.filter_by(match_id=match_id, game_num=game_num, user_id=current_user.id).all()
		matches = Match.query.filter_by(match_id=match_id, user_id=current_user.id).all()
		for game in games:
			if game.game_winner != 'NA':
				# error handling
				pass
			if game.p1 == game_winner:
				game.game_winner = 'P1'
			elif game.p2 == game_winner:
				game.game_winner = 'P2'
			else:
				# error handling
				pass

		for match in matches:
			if match.p1 == game_winner:
				match.p1_wins += 1
			elif match.p2 == game_winner:
				match.p2_wins += 1
			else:
				# error handling
				pass
			if match.p1_wins > match.p2_wins:
				match.match_winner = 'P1'
			elif match.p2_wins > match.p1_wins:
				match.match_winner = 'P2'
			elif match.p1_wins == match.p2_wins:
				match.match_winner = 'NA'
			else:
				#error
				pass
		db.session.commit()

	next_game = Game.query.filter_by(user_id=current_user.id, game_winner='NA', p1=current_user.username)
	next_game = next_game.filter(Game.match_id > match_id).order_by(Game.match_id).first()
	if next_game is None:
		return {'match_id':'NA'}
	ga = GameActions.query.filter_by(user_id=current_user.id, match_id=next_game.match_id, game_num=next_game.game_num).first().game_actions.split('\n')[-15:]
	for index,i in enumerate(ga):
		string = i
		if i.count('@[') != i.count('@]'):
			continue
		for j in range(i.count('@[')):
			string = string.replace('@[','<b>',1).replace('@]','</b>',1)
		ga[index] = string
	ga_dict = {'game_actions' : ga}
	return next_game.as_dict() | ga_dict

@views.route('/game_winner_init')
def game_winner_init():
	first_game = Game.query.filter_by(user_id=current_user.id, game_winner='NA', p1=current_user.username).order_by(Game.match_id).first()
	if first_game is None:
		return {'match_id':'NA'}
	ga = GameActions.query.filter_by(user_id=current_user.id, match_id=first_game.match_id, game_num=first_game.game_num).first().game_actions.split('\n')[-15:]
	for index,i in enumerate(ga):
		string = i
		if i.count('@[') != i.count('@]'):
			continue
		for j in range(i.count('@[')):
			string = string.replace('@[','<b>',1).replace('@]','</b>',1)
		ga[index] = string
	ga_dict = {'game_actions' : ga}
	return first_game.as_dict() | ga_dict

@views.route('/draft_id_init')
def draft_id_init():
	limited_matches = Match.query.filter_by(user_id=current_user.id, draft_id='NA', p1=current_user.username)
	limited_matches = limited_matches.filter( Match.format.in_(options['Limited Formats']) ).order_by(Match.match_id)
	first_match = limited_matches.first()
	while True:
		if first_match is None:
			return {'match_id':'NA'}

		lands = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																	match_id=first_match.match_id, 
																	casting_player=first_match.p1, 
																	action='Land Drop').order_by(Play.primary_card)]
		nb_lands = [i for i in lands if (i not in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest'])]
		spells = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																	 match_id=first_match.match_id, 
																	 casting_player=first_match.p1, 
																	 action='Casts').order_by(Play.primary_card)]

		spells = list(modo.clean_card_set(set(spells), get_multifaced_cards()))

		cards_dict = {'lands':[*set(lands)], 'spells':[*set(spells)]}
		draft_ids_dict = {'possible_draft_ids':[]}

		for draft in Draft.query.filter_by(user_id=current_user.id).filter(Draft.date < first_match.date).all():
			picks = [pick.card for pick in Pick.query.filter_by(user_id=current_user.id, draft_id=draft.draft_id)]
			if all(i in picks for i in (nb_lands + spells)):
				draft_ids_dict['possible_draft_ids'].append(draft.draft_id)

		if len(draft_ids_dict['possible_draft_ids']) > 0:
			break
			#return {'match_id':'NA'}

		limited_matches = limited_matches.filter(Match.match_id > first_match.match_id).order_by(Match.match_id)
		first_match = limited_matches.first()

	return first_match.as_dict() | cards_dict | draft_ids_dict

@views.route('/associated_draft_id/<match_id>/<draft_id>')
def apply_draft_id(match_id, draft_id):
	# Add limited match conditions here.
	limited_matches = Match.query.filter_by(user_id=current_user.id, draft_id='NA', p1=current_user.username)
	limited_matches = limited_matches.filter( Match.format.in_(options['Limited Formats']) )
	limited_matches = limited_matches.filter(Match.match_id > match_id).order_by(Match.match_id)
	next_match = limited_matches.first()

	if draft_id != '0':
		matches = Match.query.filter_by(user_id=current_user.id, match_id=match_id).all()
		for match in matches:
			match.draft_id = draft_id
		db.session.commit()

		match_wins = 0
		match_losses = 0
		associated_matches = Match.query.filter_by(user_id=current_user.id, draft_id=draft_id, p1=current_user.username)
		for match in associated_matches:
			if match.p1_wins > match.p2_wins:
				match_wins += 1
			elif match.p2_wins > match.p1_wins:
				match_losses += 1
		draft = Draft.query.filter_by(user_id=current_user.id, draft_id=draft_id).first()
		draft.match_wins = match_wins
		draft.match_losses = match_losses
		db.session.commit()

	while True:
		if next_match is None:
			return {'match_id':'NA'}

		lands = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																	match_id=next_match.match_id, 
																	casting_player=next_match.p1, 
																	action='Land Drop').order_by(Play.primary_card)]
		nb_lands = [i for i in lands if (i not in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest'])]
		spells = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																	 match_id=next_match.match_id, 
																	 casting_player=next_match.p1, 
																	 action='Casts').order_by(Play.primary_card)]

		spells = list(modo.clean_card_set(set(spells), get_multifaced_cards()))

		cards_dict = {'lands':[*set(lands)], 'spells':[*set(spells)]}
		draft_ids_dict = {'possible_draft_ids':[]}

		for draft in Draft.query.filter_by(user_id=current_user.id).filter(Draft.date < next_match.date).all():
			picks = [pick.card for pick in Pick.query.filter_by(user_id=current_user.id, draft_id=draft.draft_id)]
			if all(i in picks for i in (nb_lands + spells)):
				draft_ids_dict['possible_draft_ids'].append(draft.draft_id)

		if len(draft_ids_dict['possible_draft_ids']) > 0:
			break
		
		limited_matches = limited_matches.filter(Match.match_id > next_match.match_id).order_by(Match.match_id)
		next_match = limited_matches.first()

	return next_match.as_dict() | cards_dict | draft_ids_dict

@views.route('/input_options')
def input_options():
	return get_input_options()

@views.route('/export')
def export():
	df_list = [i.as_dict() for i in Match.query.filter_by(user_id=current_user.id).all()]

	df = pd.DataFrame(df_list)

	print(df)
	return "lol"

@views.route('/best_guess', methods=['POST'])
def best_guess():
	bg_type = request.form.get('BG_Match_Set').strip()
	replace_type = request.form.get('BG_Replace').strip()
	con_count = 0
	lim_count = 0
	all_matches = Match.query.filter_by(user_id=current_user.id)
	
	if replace_type == 'Overwrite All':
		if (bg_type == 'Limited Only') or (bg_type == 'All Matches'):
			matches = all_matches.filter( Match.format.in_(options['Limited Formats']) )
			for match in matches:
				cards1 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																			 match_id=match.match_id, 
																			 casting_player=match.p1).filter( Play.action.in_(['Land Drop', 'Casts']) )]
				cards2 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																			 match_id=match.match_id, 
																			 casting_player=match.p2).filter( Play.action.in_(['Land Drop', 'Casts']) )]
				match.p1_subarch = modo.get_limited_subarch(cards1)
				match.p2_subarch = modo.get_limited_subarch(cards2)
				match.p1_arch = 'Limited'
				match.p2_arch = 'Limited'
				db.session.commit()
				lim_count += 1
		if (bg_type == 'Constructed Only') or (bg_type == 'All Matches'):
			matches = all_matches.filter( Match.format.in_(options['Constructed Formats']) )
			for match in matches:
				yyyy_mm = match.date[0:4] + "-" + match.date[5:7]
				cards1 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																			 match_id=match.match_id, 
																			 casting_player=match.p1).filter( Play.action.in_(['Land Drop', 'Casts']) )]
				cards2 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																			 match_id=match.match_id, 
																			 casting_player=match.p2).filter( Play.action.in_(['Land Drop', 'Casts']) )]
				p1_data = modo.closest_list(set(cards1),all_decks,yyyy_mm)
				p2_data = modo.closest_list(set(cards2),all_decks,yyyy_mm)
				match.p1_subarch = p1_data[0]
				match.p2_subarch = p2_data[0]
				db.session.commit()
				con_count += 1

	if replace_type == 'Replace NA/Unknown':
		all_matches = all_matches.filter( (Match.p1_subarch.in_(['Unknown', 'NA'])) | (Match.p2_subarch.in_(['Unknown', 'NA'])) )
		if (bg_type == 'Limited Only') or (bg_type == 'All Matches'):
			matches = all_matches.filter( Match.format.in_(options['Limited Formats']) )
			for match in matches:
				if match.p1_subarch in ['Unknown', 'NA']:
					cards1 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																				 match_id=match.match_id, 
																				 casting_player=match.p1).filter( Play.action.in_(['Land Drop', 'Casts']) )]
					match.p1_subarch = modo.get_limited_subarch(cards1)
					match.p1_arch = 'Limited'
					lim_count += 1
				if match.p2_subarch in ['Unknown', 'NA']:
					cards2 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																				 match_id=match.match_id, 
																				 casting_player=match.p2).filter( Play.action.in_(['Land Drop', 'Casts']) )]
					match.p2_subarch = modo.get_limited_subarch(cards2)
					match.p2_arch = 'Limited'
					lim_count += 1
				db.session.commit()
		if (bg_type == 'Constructed Only') or (bg_type == 'All Matches'):
			matches = all_matches.filter( Match.format.in_(options['Constructed Formats']) )
			for match in matches:
				yyyy_mm = match.date[0:4] + "-" + match.date[5:7]
				if match.p1_subarch in ['Unknown', 'NA']:
					cards1 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																				 match_id=match.match_id, 
																				 casting_player=match.p1).filter( Play.action.in_(['Land Drop', 'Casts']) )]
					p1_data = modo.closest_list(set(cards1),all_decks,yyyy_mm)
					match.p1_subarch = p1_data[0]
					con_count += 1
				if match.p2_subarch in ['Unknown', 'NA']:
					cards2 = [play.primary_card for play in Play.query.filter_by(user_id=current_user.id, 
																				 match_id=match.match_id, 
																				 casting_player=match.p2).filter( Play.action.in_(['Land Drop', 'Casts']) )]
					p2_data = modo.closest_list(set(cards2),all_decks,yyyy_mm)
					match.p2_subarch = p2_data[0]
					con_count += 1
				db.session.commit()

	flash(f'{con_count} constructed decks revised, {lim_count} limited decks revised.', category='success')
	return redirect("/table/matches/1")

@views.route('/remove', methods=['POST'])
def remove():
	removeType = request.form.get('removeType')
	match_id = request.form.get('removeMatchId')

	match_size = Match.query.filter_by(user_id=current_user.id, match_id=match_id).count()
	game_size = Game.query.filter_by(user_id=current_user.id, match_id=match_id).count()
	play_size = Play.query.filter_by(user_id=current_user.id, match_id=match_id).count()

	Match.query.filter_by(user_id=current_user.id, match_id=match_id).delete()
	Game.query.filter_by(user_id=current_user.id, match_id=match_id).delete()
	Play.query.filter_by(user_id=current_user.id, match_id=match_id).delete()

	if removeType == 'Ignore':
		newIgnore = Removed(user_id=current_user.id, match_id=match_id, ignored=True)
		db.session.add(newIgnore)

	db.session.commit()

	flash(f'{match_size} Matches removed, {game_size} Games removed, {play_size} Plays removed.', category='success')
	return redirect('/table/matches/1')

@views.route('/profile')
def profile():
	return render_template('profile.html', user=current_user)

@views.route('/edit_profile', methods=['POST'])
def edit_profile():
	new_email = request.form.get('ProfileEmailInputText')
	new_name = request.form.get('ProfileNameInputText')
	new_username = request.form.get('ProfileUsernameInputText').strip()

	user = User.query.filter_by(id=current_user.id).first()
	user.email = new_email
	user.username = new_username
	db.session.commit()
	
	return redirect('/profile')

@views.route('/dashboards/<dash_name>', methods=['GET', 'POST'])
def dashboards(dash_name):
	def match_result(p1_wins, p2_wins):
		if p1_wins == p2_wins:
			return f'NA {p1_wins}-{p2_wins}'
		elif p1_wins > p2_wins:
			return f'Win {p1_wins}-{p2_wins}'
		elif p2_wins > p1_wins:
			return f'Loss {p1_wins}-{p2_wins}'
	def format_string(fmt, limited_format):
		if fmt in options['Limited Formats']:
			return f'{fmt}: {limited_format}'
		return f'{fmt}'

	if request.method == 'POST':
		dashCard = request.form.get('dashCard')
		dashOpponent = request.form.get('dashOpponent')
		dashFormat = request.form.get('dashFormat')
		dashLimitedFormat = request.form.get('dashLimitedFormat')
		dashDeck = request.form.get('dashDeck')
		dashOppDeck = request.form.get('dashOppDeck')
		dashDate1 = request.form.get('dashDate1')
		dashDate2 = request.form.get('dashDate2')
	else:
		dashCard = 'Card'
		dashOpponent = 'Opponent'
		dashFormat = 'Format'
		dashLimitedFormat = 'Limited Format'
		dashDeck = 'Deck'
		dashOppDeck = 'Opp. Deck'
		dashDate1 = 'Date1'
		dashDate2 = 'Date2'
	inputs = [dashCard, dashOpponent, dashFormat, dashLimitedFormat, dashDeck, dashOppDeck, dashDate1, dashDate2]

	table = Match.query.filter_by(user_id=current_user.id, p1=current_user.username)
	if dashOpponent != 'Opponent':
		table = table.filter_by(p2=dashOpponent)
	if dashFormat != 'Format':
		table = table.filter_by(format=dashFormat)
	if dashLimitedFormat != 'Limited Format':
		table = table.filter_by(limited_format=dashLimitedFormat)
	if dashDeck != 'Deck':
		table = table.filter_by(p1_subarch=dashDeck)
	if dashOppDeck != 'Opp. Deck':
		table = table.filter_by(p2_subarch=dashOppDeck)

	if dash_name == 'match_history':
		pass
	elif dash_name == 'match_stats':
		pass
	elif dash_name == 'game_stats':
		table = table.join(Game, (Game.user_id == Match.user_id) & (Game.match_id == Match.match_id) & (Game.p1 == Match.p1)).add_entity(Game)
	elif dash_name == 'play_stats':
		table = table.join(Game, (Game.user_id == Match.user_id) & (Game.match_id == Match.match_id) & (Game.p1 == Match.p1)).add_entity(Game)
		table = table.join(Play, (Play.user_id == Game.user_id) & (Play.match_id == Game.match_id) & (Play.game_num == Game.game_num)).add_entity(Play)
	elif dash_name == 'opponents':
		pass
	elif dash_name == 'card_data':
		table = table.join(Game, (Game.user_id == Match.user_id) & (Game.match_id == Match.match_id) & (Game.p1 == Match.p1)).add_entity(Game)
		table = table.join(Play, (Play.user_id == Game.user_id) & (Play.match_id == Game.match_id) & (Play.game_num == Game.game_num)).add_entity(Play)
		table = table.filter(Play.action.in_(['Casts']))
		table = table.filter(Play.primary_card != 'NA')

	if dash_name == 'match_history':
		table = table.order_by(desc(Match.match_id)).limit(25)
		df = pd.DataFrame([i.as_dict() for i in table.all()])
		df['Match Result'] = df.apply(lambda x: match_result(p1_wins=x['p1_wins'], p2_wins=x['p2_wins']), axis=1)
		df['Match Format'] = df.apply(lambda x: format_string(fmt=x['format'], limited_format=x['limited_format']), axis=1)
		df = df.rename(columns={'p2':'Opponent', 'p2_subarch':'Opp. Deck', 'p1_subarch':'Deck', 'date':'Date'})
		df = df[['Date','Opponent','Deck','Opp. Deck','Match Result','Match Format']]
		return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs, table=[df])
	elif dash_name == 'match_stats':
		df = pd.DataFrame([i.as_dict() for i in table.all()])
		df['Wins'] = df.apply(lambda x: 1 if x['match_winner'] == 'P1' else 0, axis=1)
		df['Losses'] = df.apply(lambda x: 1 if x['match_winner'] == 'P2' else 0, axis=1)
		df['Roll_Wins'] = df.apply(lambda x: 1 if x['roll_winner'] == 'P1' else 0, axis=1)
		df['Roll_Losses'] = df.apply(lambda x: 1 if x['roll_winner'] == 'P2' else 0, axis=1)

		df1 = df.groupby(['format']).agg({'Wins':'sum', 'Losses':'sum'}).reset_index()
		df1 = df1.rename(columns={'format':'Description'})
		df1.loc[-1] = pd.concat([pd.Series({'Description':'Match Format'}), df[['Wins','Losses']].sum()], axis=0)
		df1.index = df1.index + 1
		df1 = df1.sort_index()
		df1['Match Win%'] = df1.apply(lambda x: round( (x['Wins']/(x['Wins']+x['Losses']))*100, 1), axis=1)

		df2 = df.groupby(['match_type']).agg({'Wins':'sum', 'Losses':'sum'}).reset_index()
		df2 = df2.rename(columns={'match_type':'Description'})
		df2.loc[-1] = pd.concat([pd.Series({'Description':'Match Type'}), df[['Wins','Losses']].sum()], axis=0)
		df2.index = df2.index + 1
		df2 = df2.sort_index()
		df2['Match Win%'] = df2.apply(lambda x: round( (x['Wins']/(x['Wins']+x['Losses']))*100, 1), axis=1)

		df3 = df.groupby(['p1_subarch']).agg({'p1':'count', 'Wins':'sum', 'Losses':'sum'}).reset_index()
		df3 = df3.rename(columns={'p1':'Share', 'p1_subarch':'Decks'})
		df3['Match Win%'] = df3.apply(lambda x: round( (x['Wins']/(x['Wins']+x['Losses']))*100, 1), axis=1)
		df3['Share'] = df3.apply(lambda x: str(x['Share']) + ' - (' + str(round( (x['Share']/df3['Share'].sum())*100)) + '%)', axis=1)

		df4 = df.groupby(['p2_subarch']).agg({'p2':'count', 'Wins':'sum', 'Losses':'sum'}).reset_index()
		df4 = df4.rename(columns={'p2':'Share', 'p2_subarch':'Decks'})
		df4['Win% Against'] = df4.apply(lambda x: round( (x['Wins']/(x['Wins']+x['Losses']))*100, 1), axis=1)
		df4['Share'] = df4.apply(lambda x: str(x['Share']) + ' - (' + str(round( (x['Share']/df4['Share'].sum())*100)) + '%)', axis=1)

		df5 = pd.DataFrame({'Die Rolls':['Hero - Mean', 'Opp. - Mean', '-', 'Hero - Win%'], '-':[round(df['p1_roll'].mean(),2), round(df['p2_roll'].mean(),2), '-', round((df['Roll_Wins'].sum()/(df['Roll_Wins'].sum()+df['Roll_Losses'].sum())*100 ),1)]})
		return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs, table=[df1, df2, df3, df4, df5])
	elif dash_name == 'game_stats':
		df = pd.DataFrame([i[0].as_dict() | i[1].as_dict() for i in table.all()])
		df['PD_Label'] = df.apply(lambda x: 'Play' if x['on_play'] == 'P1' else 'Draw', axis=1)
		df['PD_Label2'] = 'Overall'
		df['Game_Label'] = df.apply(lambda x: 'Game 1' if x['game_num'] == 1 else ('Game 2' if x['game_num'] == 2 else ('Game 3' if x['game_num'] == 3 else 0)), axis=1)
		df['Game_Label2'] = 'All Games'
		df['Wins'] = df.apply(lambda x: 1 if x['game_winner'] == 'P1' else 0, axis=1)
		df['Losses'] = df.apply(lambda x: 1 if x['game_winner'] == 'P2' else 0, axis=1)

		df1 = df.groupby(['Game_Label', 'PD_Label']).agg({'Wins':'sum', 'Losses':'sum', 'p1':'count', 'p1_mulls':'mean', 'p2_mulls':'mean', 'turns':'mean'}).reset_index()
		df1_total = df.groupby(['Game_Label', 'PD_Label2']).agg({'Wins':'sum', 'Losses':'sum', 'p1':'count', 'p1_mulls':'mean', 'p2_mulls':'mean', 'turns':'mean'}).reset_index()
		df1_total = df1_total.rename(columns={'PD_Label2':'PD_Label'})
		df2 = df.groupby(['Game_Label2', 'PD_Label']).agg({'Wins':'sum', 'Losses':'sum', 'p1':'count', 'p1_mulls':'mean', 'p2_mulls':'mean', 'turns':'mean'}).reset_index()
		df2_total = df.groupby(['Game_Label2', 'PD_Label2']).agg({'Wins':'sum', 'Losses':'sum', 'p1':'count', 'p1_mulls':'mean', 'p2_mulls':'mean', 'turns':'mean'}).reset_index()
		df2 = df2.rename(columns={'Game_Label2':'Game_Label', 'PD_Label2':'PD_Label'})
		df2_total = df2_total.rename(columns={'Game_Label2':'Game_Label', 'PD_Label2':'PD_Label'})
		df3 = pd.concat([df1, df1_total, df2, df2_total]).reset_index(drop=True)
		df3['p1_mulls'] = df3.apply(lambda x: round(x['p1_mulls'],2), axis=1)
		df3['p2_mulls'] = df3.apply(lambda x: round(x['p2_mulls'],2), axis=1)
		df3['turns'] = df3.apply(lambda x: round(x['turns'],2), axis=1)
		df3['Win%'] = df3.apply(lambda x: round( (x['Wins']/(x['Wins']+x['Losses']))*100, 1), axis=1)
		df3['Ordered'] = pd.Categorical(df3['PD_Label'], categories=['Play', 'Draw', 'Overall'], ordered=True)
		df3 = df3.rename(columns={'p1':'Total', 'p1_mulls':'Mulls/G', 'p2_mulls':'Opp Mulls/G', 'turns':'Turns/G'})
		df3 = df3.sort_values(['Game_Label', 'Ordered'], ascending=True).drop('Ordered', axis=1).reset_index(drop=True)

		return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs, table=[df3])
	elif dash_name == 'play_stats':
		df = pd.DataFrame([i[0].as_dict() | i[1].as_dict() | i[2].as_dict() for i in table.all()])
		#for i in table.all():
		#	print(i)

		return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs, table=[df.head(25)]) 
	elif dash_name == 'opponents':
		pass 
	elif dash_name == 'card_data':
		#table = table.filter(Game.game_num.in_([1]))
		df_pre = pd.DataFrame([i[0].as_dict() | i[1].as_dict() | i[2].as_dict() for i in table.filter(Game.game_num.in_([1])).all()])
		df_pre['Games Won'] = df_pre.apply(lambda x: x['match_id']+str(x['game_num']) if x['game_winner'] == 'P1' else None, axis=1)
		df_pre['Games Played'] = df_pre.apply(lambda x: x['match_id']+str(x['game_num']), axis=1)

		df_post = pd.DataFrame([i[0].as_dict() | i[1].as_dict() | i[2].as_dict() for i in table.filter(Game.game_num.in_([2,3])).all()])
		df_post['Games Won'] = df_post.apply(lambda x: x['match_id']+str(x['game_num']) if x['game_winner'] == 'P1' else None, axis=1)
		df_post['Games Played'] = df_post.apply(lambda x: x['match_id']+str(x['game_num']), axis=1)

		df1 = df_pre.groupby(['primary_card']).agg({'Games Won':'nunique', 'Games Played':'nunique'}).reset_index()
		df1['Game Win%'] = df1.apply(lambda x: round((x['Games Won']/x['Games Played'])*100,1), axis=1)
		df1 = df1.sort_values(by='Games Played', ascending=False).reset_index(drop=True)

		df2 = df_post.groupby(['primary_card']).agg({'Games Won':'nunique', 'Games Played':'nunique'}).reset_index()
		df2['Game Win%'] = df2.apply(lambda x: round((x['Games Won']/x['Games Played'])*100,1), axis=1)
		df2 = df2.sort_values(by='Games Played', ascending=False).reset_index(drop=True)

		return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs, table=[df1.head(25), df2.head(25)]) 

	return render_template('dashboards.html', user=current_user, dash_name=dash_name, inputs=inputs)

@views.route('/filter_options')
def filter_options():
	filter_options_dict = {}
	table = Match.query.filter_by(user_id=current_user.id, p1=current_user.username)

	filter_options_dict['Opponent'] = [i.p2 for i in table.with_entities(Match.p2).distinct().order_by(Match.p2).all()]
	filter_options_dict['Format'] = [i.format for i in table.with_entities(Match.format).distinct().order_by(Match.format).all()]
	filter_options_dict['Limited Format'] = [i.limited_format for i in table.with_entities(Match.limited_format).distinct().order_by(Match.limited_format).all()]
	filter_options_dict['Deck'] = [i.p1_subarch for i in table.with_entities(Match.p1_subarch).distinct().order_by(Match.p1_subarch).all()]
	filter_options_dict['Opp. Deck'] = [i.p2_subarch for i in table.with_entities(Match.p2_subarch).distinct().order_by(Match.p2_subarch).all()]
	#filter_options_dict['Date1'] = [i.p2 for i in table.with_entities(Match.p2).distinct().order_by(Match.p2).all()]
	#filter_options_dict['Date2'] = [i.p2 for i in table.with_entities(Match.p2).distinct().order_by(Match.p2).all()]
	return filter_options_dict

@views.route('/generate_plot', methods=['POST'])
def generate_plot():
	print(request.form)
	dashOpponent = request.form.get('dashOpponent')
	dashFormat = request.form.get('dashFormat')
	dashLimitedFormat = request.form.get('dashLimitedFormat')
	dashDeck = request.form.get('dashDeck')
	dashOppDeck = request.form.get('dashOppDeck')
	dashDate1 = request.form.get('dashDate1')
	dashDate2 = request.form.get('dashDate2')
	inputs = [dashOpponent, dashFormat, dashLimitedFormat, dashDeck, dashOppDeck, dashDate1, dashDate2]

	return render_template('dashboards.html', user=current_user, dash_name=request.form.get('dashName'), inputs=inputs)