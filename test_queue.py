from bot import DJ


def test_queue():
	dj = DJ()
	dj.enqueue(1, 'avm', '01')
	dj.enqueue(1, 'avm', '03')
	dj.enqueue(2, 'alice', '02')
	dj.enqueue(2, 'alice', '04')
	assert dj.next() == 'Next up: 01 (by avm)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 02 (by alice)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 03 (by avm)\nCommands: /next /listall /remove'
	dj.enqueue(3, 'guest1', '01')
	dj.enqueue(3, 'guest1', '02')
	assert dj.next() == 'Next up: 01 (by guest1)\nCommands: /next /listall /remove'
	dj.enqueue(3, 'guest1', '03')
	dj.enqueue(4, 'guest2', '04')
	assert dj.next() == 'Next up: 04 (by guest2)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 04 (by alice)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 02 (by guest1)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 03 (by guest1)\nCommands: /next /listall /remove'
	assert dj.next() == 'The queue is empty'

def test_clear():
	dj = DJ()
	dj.enqueue(1, 'avm', '01')
	dj.enqueue(1, 'avm', '03')
	dj.enqueue(2, 'alice', '02')
	dj.enqueue(2, 'alice', '04')
	dj.clear(1)
	assert dj.next() == 'Next up: 02 (by alice)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 04 (by alice)\nCommands: /next /listall /remove'

def test_remove():
	dj = DJ()
	dj.enqueue(1, 'avm', '01')
	dj.enqueue(1, 'avm', '03')
	dj.enqueue(2, 'alice', '02')
	dj.enqueue(2, 'alice', '04')
	assert dj.next() == 'Next up: 01 (by avm)\nCommands: /next /listall /remove'
	assert dj.remove() == 'avm removed from the queue'
	assert dj.next() == 'Next up: 02 (by alice)\nCommands: /next /listall /remove'
	assert dj.next() == 'Next up: 04 (by alice)\nCommands: /next /listall /remove'
