from itertools import cycle
import random
import sys
import pygame
from pygame.locals import *

import qrcode
from io import BytesIO
from PIL import Image
from auth import build_auth_url, check_auth, is_authorized, init_logging, get_auth_meta, logout
import schedule

from learedboard import save_score

FPS = 30
SCREENWIDTH  = 288 * 2
SCREENHEIGHT = 1080
PIPEGAPSIZE  = 230 # gap between upper and lower part of pipe
FULLSCREEN_WIDTH = 1000
BASEY        = SCREENHEIGHT * 0.79
# image, sound and hitmask  dicts
IMAGES, SOUNDS, HITMASKS = {}, {}, {}
PIPE_VEL = 128
SCORE = 0

JUMP_KEYS = []

# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # red bird
    (
        'assets/sprites/redbird-upflap.png',
        'assets/sprites/redbird-midflap.png',
        'assets/sprites/redbird-downflap.png',
    ),
    # blue bird
    (
        'assets/sprites/bluebird-upflap.png',
        'assets/sprites/bluebird-midflap.png',
        'assets/sprites/bluebird-downflap.png',
    ),
    # yellow bird
    (
        'assets/sprites/yellowbird-upflap.png',
        'assets/sprites/yellowbird-midflap.png',
        'assets/sprites/yellowbird-downflap.png',
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    'assets/sprites/background-day.png',
    'assets/sprites/background-night.png',
)

# list of pipes
PIPES_LIST = (
    'assets/sprites/pipe-green.png',
    'assets/sprites/pipe-red.png',
)


try:
    xrange
except NameError:
    xrange = range

def get_inner_x() -> int:
    width = IMAGES['background'].get_width()
    return int((FULLSCREEN_WIDTH - width) / 2)

def generate_QR(url: str):
    qr = qrcode.QRCode(
    version = 1,
    error_correction = qrcode.constants.ERROR_CORRECT_H,
    box_size = 10,
    border = 4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image()
    return img

QR = None

def get_game_area() -> (int, int, int, int):
    back_rect = IMAGES['background'].get_rect(topleft=(get_inner_x(), 0))
    return (back_rect[0], back_rect[1], back_rect[2], SCREENHEIGHT)

def draw_qr() -> None:
    SCREEN.blit(QR,(FULLSCREEN_WIDTH / 2 - QR.get_width() / 2 , SCREENHEIGHT / 2 + int(SCREENHEIGHT * 0.1)))

LOCK = False

def _generate_new_qr(url) -> None:
    global QR, LOCK

    if LOCK:
        return

    LOCK = True
    img = generate_QR(url)
    buffered = BytesIO()
    img.save(buffered, format="PNG")

    pilimage = Image.open(buffered).convert("RGBA")
    qr = pygame.image.fromstring(pilimage.tobytes(), pilimage.size, pilimage.mode).convert()
    QR = scale(qr, scale_factor = 0.75)
    LOCK = False

def generate_new_qr() -> None:
    from threading import Thread
    thread = Thread(target = lambda: _generate_new_qr(build_auth_url()))
    thread.start()

def init_game() -> None:
    global SCREEN, FPSCLOCK
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    SCREEN = pygame.display.set_mode((FULLSCREEN_WIDTH, SCREENHEIGHT), RESIZABLE | DOUBLEBUF, 16)
    pygame.event.set_allowed([QUIT, KEYDOWN])
    pygame.display.set_caption('Portal Bird')

def scale(image: "Surface", scale_factor = 2) -> "Surface":
    size = image.get_size()
    return pygame.transform.scale(image, (int(size[0]*scale_factor), int(size[1]*scale_factor)))

def preload_data() -> None:
    # numbers sprites for score display
    IMAGES["numbers"] = (
        pygame.image.load('assets/sprites/0.png').convert_alpha(),
        pygame.image.load('assets/sprites/1.png').convert_alpha(),
        pygame.image.load('assets/sprites/2.png').convert_alpha(),
        pygame.image.load('assets/sprites/3.png').convert_alpha(),
        pygame.image.load('assets/sprites/4.png').convert_alpha(),
        pygame.image.load('assets/sprites/5.png').convert_alpha(),
        pygame.image.load('assets/sprites/6.png').convert_alpha(),
        pygame.image.load('assets/sprites/7.png').convert_alpha(),
        pygame.image.load('assets/sprites/8.png').convert_alpha(),
        pygame.image.load('assets/sprites/9.png').convert_alpha()
    )
    # game over sprite
    IMAGES['gameover'] = pygame.image.load('assets/sprites/gameover.png').convert_alpha()
    # message sprite for welcome screen
    IMAGES['message'] = pygame.image.load('assets/sprites/message.png').convert_alpha()
    IMAGES['qr_message'] = pygame.image.load('assets/sprites/qr_message.png').convert_alpha()
    # base (ground) sprite
    IMAGES['base'] = pygame.image.load('assets/sprites/base.png').convert_alpha()

    if 'win' in sys.platform:
        soundExt = '.wav'
    else:
        soundExt = '.ogg'

    # sounds
    SOUNDS['die']    = pygame.mixer.Sound('assets/audio/die' + soundExt)
    SOUNDS['hit']    = pygame.mixer.Sound('assets/audio/hit' + soundExt)
    SOUNDS['point']  = pygame.mixer.Sound('assets/audio/point' + soundExt)
    SOUNDS['swoosh'] = pygame.mixer.Sound('assets/audio/swoosh' + soundExt)
    SOUNDS['wing']   = pygame.mixer.Sound('assets/audio/wing' + soundExt)

def scale_init(number: int) -> None:
    IMAGES["numbers"] = tuple(scale(image) for image in IMAGES["numbers"])

    IMAGES['base'] = scale(IMAGES['base'])
    IMAGES['message'] = scale(IMAGES['message'])
    IMAGES['qr_message'] = scale(IMAGES['qr_message'])
    IMAGES['gameover'] = scale(IMAGES['gameover'])

def scale_player_background_pipe() -> None:
    IMAGES['player'] = tuple(scale(image) for image in IMAGES["player"])
    IMAGES['pipe'] = tuple(scale(image) for image in IMAGES["pipe"])

    IMAGES['background'] = scale(IMAGES['background'])

def logout_and_save_score() -> None:
    if is_authorized():
        name, img = get_auth_meta()
        save_score(name, img, SCORE)
    logout()

def main():
    init_game()
    preload_data()

    scale_init(1)

    while True:
        # select random background sprites
        randBg = random.randint(0, len(BACKGROUNDS_LIST) - 1)
        IMAGES['background'] = pygame.image.load(BACKGROUNDS_LIST[randBg]).convert()

        # select random player sprites
        randPlayer = random.randint(0, len(PLAYERS_LIST) - 1)
        IMAGES['player'] = (
            pygame.image.load(PLAYERS_LIST[randPlayer][0]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][1]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][2]).convert_alpha(),
        )

        # select random pipe sprites
        pipeindex = random.randint(0, len(PIPES_LIST) - 1)
        IMAGES['pipe'] = (
            pygame.transform.flip(
                pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(), False, True),
            pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(),
        )
        scale_player_background_pipe()


        # hitmask for pipes
        HITMASKS['pipe'] = (
            getHitmask(IMAGES['pipe'][0]),
            getHitmask(IMAGES['pipe'][1]),
        )

        # hitmask for player
        HITMASKS['player'] = (
            getHitmask(IMAGES['player'][0]),
            getHitmask(IMAGES['player'][1]),
            getHitmask(IMAGES['player'][2]),
        )

        init_background()
        pygame.display.update()

        for lives_count in range(3):
            movementInfo = showWelcomeAnimation()

            if not is_authorized():
                break

            crashInfo = mainGame(movementInfo)

            if not is_authorized():
                break

            showGameOverScreen(crashInfo)
            if not is_authorized():
                break

        logout_and_save_score()


def init_background() -> ("Surface", "Surface"):
    start_x = 0
    start_y = 0

    end_x = get_inner_x()
    end_y = SCREENHEIGHT

    left = pygame.draw.rect(SCREEN, [242, 242, 242], [start_x, start_y, end_x, end_y], 0)
    right = pygame.draw.rect(SCREEN, [242, 242, 242], [end_x + IMAGES['background'].get_width(), 0, end_x, end_y], 0)

    return (left, right)

def is_jump_pressed(event) -> bool:
    return event.type == KEYDOWN and (event.key == K_SPACE or event.key == K_UP or event.key == 1073741902) or event.type == MOUSEBUTTONDOWN

def move_base(x: int, dt: int) -> int:
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()
    return (x + PIPE_VEL * dt) % baseShift

def showWelcomeAnimation():
    """Shows welcome screen animation of flappy bird"""
    # index of player to blit on screen
    playerIndex = 0
    playerIndexGen = cycle([0, 1, 2, 1])
    # iterator used to change playerIndex after every 5th iteration
    loopIter = 0

    central_delta = get_inner_x()

    playerx = central_delta + int(SCREENWIDTH * 0.2)
    playery = int((SCREENHEIGHT - IMAGES['player'][0].get_height()) / 2)

    messagex = central_delta + int((SCREENWIDTH - IMAGES['message'].get_width()) / 2)
    messagey = int(SCREENHEIGHT * 0.12)

    basex = 0

    # player shm for up-down motion on welcome screen
    playerShmVals = {'val': 0, 'dir': 1}

    schedule.every(250).seconds.do(lambda: generate_new_qr())
    schedule.every(2).seconds.do(check_auth)
    generate_new_qr()

    while 1:
        dt = FPSCLOCK.tick(FPS) / 1000
        for event in pygame.event.get():

            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()

            if (is_authorized()):

                if is_jump_pressed(event):
                    # make first flap sound and return values for mainGame
                    SOUNDS['wing'].play()
                    return {
                        'playery': playery + playerShmVals['val'],
                        'basex': basex,
                        'playerIndexGen': playerIndexGen,
                        'player_x': playerx
                    }

            if event.type == KEYDOWN and event.key == K_DOWN:
                generate_new_qr()


        # adjust playery, playerIndex, basex
        if (loopIter + 1) % 5 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = move_base(basex, dt)

        playerShm(playerShmVals)

        # draw sprites
        SCREEN.blit(IMAGES['background'], (central_delta, 0))
        SCREEN.blit(IMAGES['player'][playerIndex],
                    (playerx, playery + playerShmVals['val']))
        SCREEN.blit(IMAGES['base'], (central_delta - basex, BASEY))

        if (is_authorized()):
            SCREEN.blit(IMAGES['message'], (messagex, messagey))
        else:
            SCREEN.blit(IMAGES['qr_message'], (messagex, messagey))
            schedule.run_pending()
            if QR is not None:
                draw_qr()

        pygame.display.update(get_game_area())

def mainGame(movementInfo):
    central_delta = get_inner_x()

    score = playerIndex = loopIter = 0
    playerIndexGen = movementInfo['playerIndexGen']
    playerx, playery = movementInfo['player_x'], movementInfo['playery']

    basex = movementInfo['basex']

    # get 2 new pipes to add to upperPipes lowerPipes list
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()

    # list of upper pipes
    upperPipes = [
        {'x': central_delta + SCREENWIDTH + 200, 'y': newPipe1[0]['y'], 'pipe_id': 1},
        {'x': central_delta + SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[0]['y'], 'pipe_id': 2},
    ]

    # list of lowerpipe
    lowerPipes = [
        {'x': central_delta + SCREENWIDTH + 200, 'y': newPipe1[1]['y'], 'pipe_id': 1},
        {'x': central_delta + SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[1]['y'], 'pipe_id': 2},
    ]

    # player velocity, max velocity, downward acceleration, acceleration on flap
    playerVelY    =  -18   # player's velocity along Y, default same as playerFlapped
    playerMaxVelY =  20   # max vel along Y, max descend speed
    playerMinVelY =  -8   # min vel along Y, max ascend speed
    playerAccY    =   2   # players downward acceleration
    playerRot     =  45   # player's rotation
    playerVelRot  =   3   # angular speed
    playerRotThr  =  20   # rotation threshold
    playerFlapAcc =  -18   # players speed on flapping
    playerFlapped = False # True when player flaps

    collided_pipes = set()

    while 1:
        dt = FPSCLOCK.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            if is_jump_pressed(event):
                if playery > -2 * IMAGES['player'][0].get_height():
                    playerVelY = playerFlapAcc
                    playerFlapped = True
                    SOUNDS['wing'].play()

        # check for crash here
        crashTest = checkCrash({'x': playerx, 'y': playery, 'index': playerIndex},
                               upperPipes, lowerPipes)
        if crashTest[0]:
            return {
                'y': playery,
                'groundCrash': crashTest[1],
                'basex': basex,
                'upperPipes': upperPipes,
                'lowerPipes': lowerPipes,
                'score': score,
                'playerVelY': playerVelY,
                'playerRot': playerRot
            }

        # check for score
        playerMidPos = playerx + IMAGES['player'][0].get_width() / 2
        for pipe in upperPipes:
            pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2
            if playerMidPos >= pipeMidPos and pipe["pipe_id"] not in collided_pipes:
                score += 1
                global SCORE
                SCORE = score
                SOUNDS['point'].play()
                collided_pipes.add(pipe["pipe_id"])

        # playerIndex basex change
        if (loopIter + 1) % 3 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = move_base(basex, dt)

        # rotate the player
        if playerRot > -90:
            playerRot -= playerVelRot

        # player's movement
        if playerVelY < playerMaxVelY and not playerFlapped:
            playerVelY += playerAccY
        if playerFlapped:
            playerFlapped = False

            # more rotation to cover the threshold (calculated in visible rotation)
            playerRot = 45

        playerHeight = IMAGES['player'][playerIndex].get_height()
        playery += min(playerVelY, BASEY - playery - playerHeight)

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe['x'] -= PIPE_VEL * dt
            lPipe['x'] -= PIPE_VEL * dt

        # add new pipe when first pipe is about to touch left of screen
        if len(upperPipes) == 1:
            newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if len(upperPipes) > 0 and upperPipes[0]['x'] < central_delta - IMAGES['pipe'][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        # draw sprites
        SCREEN.blit(IMAGES['background'], (central_delta, 0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (central_delta - basex, BASEY))
        # print score so player overlaps the score
        showScore(score)

        # Player rotation has a threshold
        visibleRot = playerRotThr
        if playerRot <= playerRotThr:
            visibleRot = playerRot
        
        playerSurface = pygame.transform.rotate(IMAGES['player'][playerIndex], visibleRot)
        SCREEN.blit(playerSurface, (playerx, playery))


        pygame.display.update(get_game_area())


def showGameOverScreen(crashInfo):
    """crashes the player down and shows gameover image"""
    central_delta = get_inner_x()

    score = crashInfo['score']
    playerx = central_delta + SCREENWIDTH * 0.2
    playery = crashInfo['y']
    playerHeight = IMAGES['player'][0].get_height()
    playerVelY = crashInfo['playerVelY']
    playerAccY = 2
    playerRot = crashInfo['playerRot']
    playerVelRot = 7

    basex = crashInfo['basex']

    upperPipes, lowerPipes = crashInfo['upperPipes'], crashInfo['lowerPipes']

    # play hit and die sounds
    SOUNDS['hit'].play()
    if not crashInfo['groundCrash']:
        SOUNDS['die'].play()

    while 1:
        dt = FPSCLOCK.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            if is_jump_pressed(event):
                return

        # player y shift
        if playery + playerHeight < BASEY - 1:
            playery += playerVelY

        # player velocity change
        if playerVelY < 15:
            playerVelY += playerAccY * dt

        # rotate only when it's a pipe crash
        if not crashInfo['groundCrash']:
            if playerRot > -90:
                playerRot -= playerVelRot

        # draw sprites
        SCREEN.blit(IMAGES['background'], (central_delta,0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (central_delta - basex, BASEY))
        showScore(score)

        playerSurface = pygame.transform.rotate(IMAGES['player'][1], playerRot)
        SCREEN.blit(playerSurface, (playerx,playery))
        SCREEN.blit(IMAGES['gameover'], (central_delta + 100, 280))

        pygame.display.update(get_game_area())


def playerShm(playerShm):
    """oscillates the value of playerShm['val'] between 8 and -8"""
    if abs(playerShm['val']) == 8:
        playerShm['dir'] *= -1

    if playerShm['dir'] == 1:
         playerShm['val'] += 1
    else:
        playerShm['val'] -= 1

_PIPE_ID = 5

def getRandomPipe():
    """returns a randomly generated pipe"""
    global _PIPE_ID

    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = get_inner_x() + SCREENWIDTH + 10
    _PIPE_ID += 1

    return [
        {'x': pipeX, 'y': gapY - pipeHeight, 'pipe_id': _PIPE_ID},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE, 'pipe_id': _PIPE_ID}, # lower pipe
    ]


def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = get_inner_x() + (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
        Xoffset += IMAGES['numbers'][digit].get_width()


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collides with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][0].get_width()
    player['h'] = IMAGES['player'][0].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return [True, True]
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])
        pipeW = IMAGES['pipe'][0].get_width()
        pipeH = IMAGES['pipe'][0].get_height()

        # pygame.draw.rect(SCREEN, [255, 0, 255], playerRect, 0)

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

            # pygame.draw.rect(SCREEN, [255, 0, 255], uPipeRect, 0)
            # pygame.draw.rect(SCREEN, [255, 0, 255], lPipeRect, 0)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    # print(f"{x1} {y1} {x2} {y2}")

    for x in xrange(rect.width):
        for y in xrange(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in xrange(image.get_width()):
        mask.append([])
        for y in xrange(image.get_height()):
            mask[x].append(bool(image.get_at((x,y))[3]))
    return mask

if __name__ == '__main__':
    # import cProfile
    # cProfile.run('main()')
    main()