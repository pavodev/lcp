#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import re
import sys
import lxml.etree as ET
from collections import Counter


categories = {
	'/tx/au': 'author', #8
	'/tx/ur': 'creator', #18
	# Paragraph
	'/tx/p': 'paragraph', #1
	'/tx/div/p': 'paragraph', #74
	'/tx/ul/p': 'paragraph', #94
	'/tx/p/au': 'author', #7
	'/tx/p/p': 'paragraph', #80
	'/tx/p/p/au': 'author', #95
	'/tx/p/ur': 'creator', #29
	'/tx/p/i': 'paragraph', #77
	'/tx/i': 'paragraph', #72
	'/tx/pre': 'paragraph', #41
	# Lead
	'/tx/ld/au': 'lead.author', #49
	'/tx/ld/p': 'lead.paragraph', #4
	'/tx/ld/p/au': 'lead.author', #44
	'/tx/ld/p/ur': 'lead.creator', #67
	'/tx/p/ld/p': 'lead.paragraph', #103
	# Zwischentitel
	'/tx/zt': 'crossheading', #2
	'/tx/ul/zt': 'crossheading', #93
	# Kasten
	'/tx/ka/au': 'box.author', #23
	'/tx/ka/dl/p': 'box.paragraph', #58
	'/tx/ka/ld/au': 'box.author', #82
	'/tx/ka/ld/p': 'box.lead.paragraph', #36
	'/tx/ka/ld/p/au': 'box.lead.author', #78
	'/tx/ka/ld/p/ur': 'box.lead.creator', #83
	'/tx/ka/p': 'box.paragraph', #6
	'/tx/ka/p/au': 'box.author', #27
	'/tx/ka/p/ur': 'box.creator', 
	'/tx/ka/ur': 'box.creator', 
	'/tx/ka/zt': 'box.crossheading', #10
	# Notiz (Anmerkungen, Referenzen, Kontaktinformationen oder dergleichen)
	'/tx/nt/p': 'note.paragraph', #9
	'/tx/nt/p/au': 'note.author', #52
	'/tx/nt/p/ur': 'note.creator', #61
	'/tx/ka/nt/p': 'box.note.paragraph', #32
	'/tx/ka/nt/p/au': 'note.author', #79
	'/tx/ka/nt/p/ur': 'note.creator', #98
	# Legende
	'/tx/lg/au': 'legend.author', #63
	'/tx/lg/p': 'legend.paragraph', #5
	'/tx/lg/p/au': 'legend.author', #35
	'/tx/lg/p/ur': 'legend.creator', #21
	'/tx/lg/ur': 'legend.creator', #28
	'/tx/ka/lg/au': 'legend.author', #62
	'/tx/ka/lg/p': 'legend.paragraph', #22
	'/tx/ka/lg/p/au': 'legend.author', #69
	'/tx/ka/lg/p/ur': 'legend.creator', #48
	'/tx/ka/lg/ur': 'legend.creator', #70
	# Links -> ignorieren
	'/tx/div/p/a': None, #86
	'/tx/p/a': None, #3
	'/tx/p/i/p/a': None,
	'/tx/p/p/a': None,
	'/tx/p/u/p/a': None,
	'/tx/ld/p/a': None, #55
	'/tx/zt/a': None,
	'/tx/zt/p/a': None,
	'/tx/blockquote/p/a': None,
	'/tx/ka/nt/p/a': None,
	'/tx/ka/p/a': None, #14
	'/tx/lg/p/a': None,
	'/tx/ka/lg/p/a': None,
	'/tx/nt/p/a': None,
	'/tx/i/p/a': None,
	'/tx/table/tbody/tr/td/p/a': None,
	'/tx/ul/p/a': None,
	# veraltet (dl,ds,pn,cn,fe,pe,ta,co,dc) -> alle ignorieren
	'/tx/dl/p': None,
	'/tx/dl/p/au': None,
	'/tx/dl/zt': None,
	'/tx/fe/co/cn': None,
	'/tx/fe/dc': None,
	'/tx/fe/ds': None,
	'/tx/fe/pe/pn': None,
	'/tx/fkeyw': None,
	'/tx/gkeyw': None,
	'/tx/ta/p': None,
	'/tx/ka/ta/p': None,
	'/tx/p/gkeyw': None,
	'/tx/lg/p/gkeyw': None,
	# unbekannt -> ignorieren
	'/tx/au/sm': None,
	'/tx/blockquote/p': None,
	# HTML Fragmente -> ignorieren
	'/tx/h1': None, #99
	'/tx/p/br': None, #110
	'/tx/ka/p/style': None, #112
	# pre
	'/tx/pre/lg/p': None, #97
	'/tx/pre/p': None, #66
	'/tx/pre/p/au': None, #109
	'/tx/pre/ur': None, #108
	'/tx/pre/zt': None, #88
	# Tabellen -> ignorieren
	'/tx/table/tbody/tr/td': None,
	'/tx/table/tbody/tr/td/p': None,
	'/tx/table/tbody/tr/td/table/tbody/tr/td': None,
	'/tx/table/tbody/tr/th': None,
	'/tx/table/tr/td': None,
	'/tx/table/tr/td/table/tr/td': None,
	'/tx/table/tr/td/table/tr/td/table/tr/td': None,
	'/tx/table/tr/td/table/tr/td/table/tr/td/table/tr/td': None,
	'/tx/table/tr/th': None,
	'/tx/div/table/tr/td': None,
	'/tx/div/table/tr/td/table/tr/td': None,
	'/tx/div/table/tr/td/table/tr/td/table/tr/td': None,
	'/tx/nt/p/table/tr/td': None,
	'/tx/ka/p/table/tbody/tr/td': None,
	'/tx/ka/p/table/tr/td': None,
	'/tx/ka/p/table/tr/th': None,
	'/tx/ka/table/tbody/tr/td': None,
	'/tx/ka/table/tbody/tr/th': None,
	'/tx/ka/table/tr/td': None,
	'/tx/ka/table/tr/td/em': None,
	'/tx/ka/table/tr/th': None,
	'/tx/p/table/tr/td': None,
	'/tx/p/table/tr/th': None,
	'/tx/ld/p/table/tr/td': None,
	'/tx/ka/ld/p/table/tr/td': None,
	'/tx/ka/lg/p/table/tr/td': None,
	'/tx/ka/nt/p/table/tr/td': None,
	'/tx/lg/p/table/tr/td': None,
}

debug_mode = len(sys.argv) > 1 and sys.argv[1] == 'debug'
debug_uuid = sys.argv[2] if debug_mode and len(sys.argv) > 2 else None

def debug(text):
	if debug_mode:
		sys.stderr.write(text+"\n")


def load_trgs():
	trgs = {}
	for lang in ('de', 'fr', 'it', 'rm', 'en'):
		trgs[lang] = {}
		with open('trgs/{}.tsv'.format(lang)) as fh:
			lines = fh.readlines()
			for line in lines:
				cols = line.rstrip().split("\t")
				trgs[lang][cols[0]] = float(cols[1])
	return trgs


trg_profiles = load_trgs()


def trg_match(text):
	chrs = list(text)
	trgs = Counter([chrs[i]+chrs[i+1]+chrs[i+2] for i in range(len(chrs)-2)])
	scores = {}
	for lang in trg_profiles.keys():
		scores[lang] = sum([trgs[trg]*trg_profiles[lang][trg] for trg in trgs.keys() & trg_profiles[lang].keys()])
	max_score = max([scores[lang] for lang in scores])
	if not max_score:
		return None
	return [(lang, score/max_score) for lang, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)]


def format_texts(uuid, article, language, dist):
	print("{}\tid\t{}".format(language, uuid))
	print("{}\tlang_dist\t{}".format(language, 1-dist))
	for entry in article:
		print("{}\t{}\t{}".format(language, entry[0], entry[1]))



for line in sys.stdin:
	uuid, xml = line.rstrip().split("\t")
	if debug_uuid and uuid != debug_uuid:
		continue

	debug("\n\033[46mDOC: "+uuid+"\033[0m")
	debug("\033[30;47m"+xml+"\033[0m")
	
	root = ET.fromstring(xml)
	tree = ET.ElementTree(root)
	article = []
	last_path = None
	authors = []
	for e in root.iter():
		real_path = tree.getpath(e)
		#debug("\033[45mPATH: "+real_path+", "+(last_path if last_path else "None")+"\033[0m")
		if last_path and last_path in real_path:
			debug("\033[45mPART OF PREVIOUS MATCH: "+last_path+" € "+real_path+"\033[0m")
			continue

		last_path = None
		path = re.sub('\[\d+\]', '', real_path)

		if not path in categories:
			debug("\033[41mNOT A VALID PATH\033[0m: "+path)
			text = ' '.join([x.strip() for x in e.itertext()])
			debug(text)
			continue

		if not e.text and False:
			continue

		if categories[path] == None:
			debug("\033[45mDON'T USE\033[0m: "+path)
			text = ' '.join([x.strip() for x in e.itertext()])
			debug(text)
			continue

		type = categories[path]
		debug("\033[44m\033["+("30" if type == 'par' else "37")+"m"+type+"\033[0m: "+real_path)

		text = ' '.join([x.strip() for x in e.itertext()])
		if not text:
			debug("\033[43mUNKNOWN\033[0m: "+path)
			continue

		debug(text)
		last_path = real_path
		article.append((type, text))

	if article:
		text = ' '.join([x[1] for x in article])
		lang_ident = trg_match(text)
		if not lang_ident:
			sys.stderr.write('UNUSABLE: '+uuid+"\n")
			continue
	else:
		sys.stderr.write('UNUSABLE: '+uuid+"\n")
		continue
	
	format_texts(uuid, article, lang_ident[0][0], lang_ident[1][1])

