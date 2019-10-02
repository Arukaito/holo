from logging import debug, info, warning
from datetime import datetime, timezone
import requests
import re

from .. import AbstractPollHandler
from data.models import Poll

class PollHandler(AbstractPollHandler):
	OPTION_PLUS = 'Like'
	OPTION_MINUS = 'Dislike'

	_poll_post_url = 'https://youpoll.me'
	_poll_post_headers = {'User-Agent': None}
	_poll_post_data = {'address': '',
	                   'poll-1[question]': None,
	                   'poll-1[option1]': OPTION_PLUS,
	                   'poll-1[option2]': OPTION_MINUS,
	                   'poll-1[min]': '1',
	                   'poll-1[max]': 10,
	                   'poll-1[voting-system]': '0',
	                   'poll-1[approval-validation-type]': '0',
	                   'poll-1[approval-validation-value]': '1',
	                   'poll-1[basic]': '',
	                   'voting-limits-dropdown': '3',
			   'captcha-test-checkbox': 'on',
	                   'reddit-link-karma': '0',
	                   'reddit-comment-karma': '0',
	                   'reddit-days-old': '8',
	                   'responses-input': '',
	                   }

	_poll_id_re = re.compile('youpoll.me/(\d+)', re.I)
	_poll_link = 'https://youpoll.me/{id}/'
	_poll_results_link = 'https://youpoll.me/{id}/r'

	def __init__(self):
		super().__init__("youpoll")

	def create_poll(self, title, submit, **kwargs):
		if not submit:
			return None
		#headers = _poll_post_headers
		#headers['User-Agent'] = config.useragent
		data = self._poll_post_data
		data['poll-1[question]'] = title
		#resp = requests.post(_poll_post_url, data = data, headers = headers, **kwargs)
		resp = requests.post(self._poll_post_url, data = data, **kwargs)

		if resp.ok:
			match = self._poll_id_re.search(resp.url)
			return match.group(1)
		else:
			return None

	def get_link(self, poll):
		return self._poll_link.format(id = poll.id)

	def get_results_link(self, poll):
		return self._poll_results_link.format(id = poll.id)

	def get_score(self, poll):
		debug(f"Getting score for show {poll.show_id} / episode {poll.episode}")
		response = self.request(self.get_results_link(poll), html = True)
		if response.find('div', class_='basic-type-results') is None:
			# Old style votes, 1-10 range
			value_text = response.find("span", class_="rating-mean-value").text
			num_votes = response.find("span", class_="admin-total-votes").text
			try:
				return float(value_text)
			except ValueError:
				warning(f"Invalid value '{value_text}', no score returned")
				return None
		else:
			# New style votes, %
			# Must be returned as a value in {0, 1}
			divs = response.find_all('div', class_='basic-option-wrapper')
			num_votes = int(response.find("span", class_="admin-total-votes").text)
			if num_votes == 0:
				warning('No vote recorded, no score returned')
				return None
			for div in divs:
				if div.find('span', class_='basic-option-title').text == self.OPTION_PLUS:
					value_text = div.find('span', class_='basic-option-percent').text
					score = float(value_text.strip('%')) / 100
					print(f'Score: {score}')
					return score
			error(f'Could not find the score, no score returned')
			return None

	@staticmethod
	def convert_score_str(score):
		if score is None:
			return ''
		elif score <= 1.0: # New style votes
			return f'{round(100 * score)}%'
		else:
			return str(score)
