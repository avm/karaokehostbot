from bot import DJ


def test_queue():
	dj = DJ()
	dj.enqueue(1, 'avm', '01')
	dj.enqueue(1, 'avm', '03')
	dj.enqueue(2, 'alice', '02')
	dj.enqueue(2, 'alice', '04')
	assert dj.next() == 'Next up: avm — 01'
	assert dj.next() == 'Next up: alice — 02'
	assert dj.next() == 'Next up: avm — 03'
	dj.enqueue(3, 'guest1', '01')
	dj.enqueue(3, 'guest1', '02')
	assert dj.next() == 'Next up: guest1 — 01'
	dj.enqueue(3, 'guest1', '03')
	dj.enqueue(4, 'guest2', '04')
	assert dj.next() == 'Next up: guest2 — 04'
	assert dj.next() == 'Next up: alice — 04'
	assert dj.next() == 'Next up: guest1 — 02'
	assert dj.next() == 'Next up: guest1 — 03'
	assert dj.next() == 'The queue is empty'

def test_clear():
	dj = DJ()
	dj.enqueue(1, 'avm', '01')
	dj.enqueue(1, 'avm', '03')
	dj.enqueue(2, 'alice', '02')
	dj.enqueue(2, 'alice', '04')
	dj.clear(1)
	assert dj.next() == 'Next up: alice — 02'
	assert dj.next() == 'Next up: alice — 04'
