from bot import DJ


def test_queue():
	dj = DJ()
	dj.enqueue('avm', '01')
	dj.enqueue('avm', '03')
	dj.enqueue('alice', '02')
	dj.enqueue('alice', '04')
	assert dj.next() == 'Next up: avm — 01'
	assert dj.next() == 'Next up: alice — 02'
	assert dj.next() == 'Next up: avm — 03'
	dj.enqueue('guest1', '01')
	dj.enqueue('guest1', '02')
	assert dj.next() == 'Next up: guest1 — 01'
	dj.enqueue('guest1', '03')
	dj.enqueue('guest2', '04')
	assert dj.next() == 'Next up: guest2 — 04'
	assert dj.next() == 'Next up: alice — 04'
	assert dj.next() == 'Next up: guest1 — 02'
	assert dj.next() == 'Next up: guest1 — 03'
	assert dj.next() == 'The queue is empty'
