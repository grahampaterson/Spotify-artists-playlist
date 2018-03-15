# TODO add timestamp to log
def log(message):
    f = open('log.txt', 'a')
    f.write('{}\n'.format(message))
