# -*- encoding:utf-8 -*- 
import numpy as np
import curses
import time
import locale
import signal
import sys
import logging
import math
import random
import json
import pickle

random.seed(1)

# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.basicConfig(filename='out.log', format='%(asctime)s [%(levelname)s]:%(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %I:%M:%S')
logging.basicConfig(filename='out.log', format='%(asctime)s [%(levelname)s]:%(message)s', level=logging.DEBUG,
                    datefmt='%Y-%m-%d %I:%M:%S', filemode='w')


class QLearningPingPong(object):
    def __init__(self, is_curses=False, qname=None, epsilon=0.4, save_model=True):
        if qname:
            f = open(qname, "rb")
            self.Q = pickle.load(f)
            #self.Q = json.loads("".join(f.readlines()))
            f.close()
        else:
            self.Q = {}
        self.b_height = 6
        self.b_width = 10
        self.bar_height = 1
        self.gamma = 0.5
        self.alpha = 0.1
        self.epsilon = epsilon
        self.survival_times = []
        self.score = [0, 0]
        self.is_curses = is_curses
        self.ite = 0
        self.save_model = save_model
        if self.is_curses:
            signal.signal(signal.SIGINT, self.signal_handler)
            locale.setlocale(locale.LC_ALL, '')  # set your locale
            self.screen = curses.initscr()
        self.game_init(restart=True)
        self.run()

    def signal_handler(self, signal, frame):
        if self.is_curses:
            print('You pressed Ctrl+C!')
            self.screen.getch()
            curses.endwin()
            sys.exit(0)

    def game_init(self, restart=False):
        self.ball = [int(self.b_height / 2), #+ random.choice([-1, 0, 1]),
                     int(self.b_width / 2), #+ random.choice([-1, 0, 1]),
                     random.choice([-1, 1]),
                     random.choice([-1, 1]),
                     ]
        self.bar1_y = [self.b_height / 2, 0]
        self.bar2_y = [self.b_height / 2, 0]
        # self.survival_time = 0
        if restart:
            self.ite = 0
            pass
        else:
            self.survival_times.append(self.survival_time)
            logging.info("ite,%s", self.ite)
            logging.debug("survival_times,\n%s", json.dumps(self.survival_times, indent=4))
            logging.info("survival_time,%s", self.survival_time)
            logging.info("avg_survival_times,%s", sum(self.survival_times) / float(len(self.survival_times)))
            if self.save_model:
                if self.ite % 50 == 0:
                    f = open("q_output_%s.pkl" % (self.ite), "wb")
                    pickle.dump(self.Q,f)
                    f.close()
            self.ite += 1
        self.survival_time = 0

    def check_position(self):
        reward = 0.
        if self.ball[1] == 0 \
                and self.ball[0] >= self.bar1_y[0] \
                and self.ball[0] <= self.bar1_y[0] + (self.bar_height - 1):
            self.ball[3] = 1
            reward = 1.

        elif self.ball[1] == self.b_width \
                and self.ball[0] >= self.bar2_y[0] \
                and self.ball[0] <= self.bar2_y[0] + (self.bar_height - 1):
            self.ball[3] = -1

        if self.ball[0] + self.ball[2] < 0:
            self.ball[2] = 1
        elif self.ball[0] + self.ball[2] > self.b_height:
            self.ball[2] = -1

        if self.bar1_y[0] <= 0 and self.bar1_y[1] == -1:
            self.bar1_y[1] = 0
        elif self.bar1_y[0] + (self.bar_height - 1) >= self.b_height and self.bar1_y[1] == 1:
            self.bar1_y[1] = 0

        if self.bar2_y[0] <= 0 and self.bar2_y[1] == -1:
            self.bar2_y[1] = 0
        elif self.bar2_y[0] + (self.bar_height - 1) >= self.b_height and self.bar2_y[1] == 1:
            self.bar2_y[1] = 0

        if self.ball[1] + self.ball[3] < 0:
            self.score[1] += 1
            logging.debug("player 2 win")
            return 1, -1.
        elif self.ball[1] + self.ball[3] > self.b_width:
            self.score[0] += 1
            logging.debug("player 1 win")
            return 1, 1.
        return 0, reward

    def move_bar_1_perfect(self):
        p_ball_y = self.ball[0]
        p_ball_y_dir = self.ball[2]
        if p_ball_y + p_ball_y_dir < 0:
            p_ball_y_dir = 1
        elif p_ball_y + p_ball_y_dir > self.b_height:
            p_ball_y_dir = -1
        p_ball_y += p_ball_y_dir

        if p_ball_y < self.bar1_y[0]:
            self.bar1_y[1] = -1
        elif p_ball_y > self.bar1_y[0] + (self.bar_height - 1):
            self.bar1_y[1] = 1

    def move_bar_2_perfect(self):
        p_ball_y = self.ball[0]
        p_ball_y_dir = self.ball[2]
        if p_ball_y + p_ball_y_dir < 0:
            p_ball_y_dir = 1
        elif p_ball_y + p_ball_y_dir > self.b_height:
            p_ball_y_dir = -1
        p_ball_y += p_ball_y_dir

        if p_ball_y < self.bar2_y[0]:
            self.bar2_y[1] = -1
        elif p_ball_y > self.bar2_y[0] + (self.bar_height - 1):
            self.bar2_y[1] = 1

    def move_bar_1(self, act):
        self.bar1_y[1] = act

    def move_bar(self, act):
        self.move_bar_1(act)
        self.move_bar_2_perfect()

    def update_position(self):
        self.ball[0] += self.ball[2]
        self.ball[1] += self.ball[3]

        # print "self.bar1_y",self.bar1_y
        self.bar1_y[0] += self.bar1_y[1]
        self.bar2_y[0] += self.bar2_y[1]
        # print "self.bar1_y",self.bar1_y

    def gen_board_string(self):
        board_s = u""
        for i in range(self.b_height + 1):
            if i >= self.bar1_y[0] and i <= self.bar1_y[0] + (self.bar_height - 1):
                board_s += u"■ "
            else:
                board_s += u"☐ "
            for j in range(self.b_width + 1):
                if i == self.ball[0] and j == self.ball[1]:
                    board_s += u"■"
                else:
                    board_s += u"☐"
            if i >= self.bar2_y[0] and i <= self.bar2_y[0] + (self.bar_height - 1):
                board_s += u" ■"
            else:
                board_s += u" ☐"
            board_s += u"\n"
        board_s += u"score:[%s, %s]\n" % (self.score[0], self.score[1])
        # board_s += u"%s %s, %s \n"%(self.ball,self.bar1_y, self.bar2_y)
        board_s += "ite:%s\n" % (self.ite)
        board_s += "current_survival_time:%s\n" % (self.survival_time)
        board_s += "average_survival_times:%s\n" % (
                (sum(self.survival_times[-10:]) + self.survival_time) / float(len(self.survival_times[-10:]) + 1))

        return board_s.encode('utf-8')

    def print_board(self):
        board_s = self.gen_board_string()
        if self.is_curses:
            self.screen.addstr(0, 0, board_s)
            self.screen.refresh()
        else:
            logging.debug("\n%s", board_s)
            # print board_s

    def run(self):
        bar1_action = random.choice([-1, 0, 1])
        while True:
            self.survival_time += 1
            self.print_board()
            self.move_bar(bar1_action)
            q_str1 =  (tuple(self.ball), self.bar1_y[0], self.bar1_y[1])
            q_current = self.Q.get(q_str1, 0.)
            q_miss, q_reward = self.check_position()
            if q_miss != 0:
                if self.is_curses:
                    time.sleep(0.5)
                self.game_init()
                self.Q.update({q_str1: q_current + self.alpha * q_reward})
                logging.debug("q_str1,%s", q_str1)
            else:
                self.update_position()
                #max_q = -99999.
                #max_a = 0
                actions = [-1, 0, 1]
                random.shuffle(actions)
                all_qa = []
                for q_action2 in actions:
                    q_str2 =  (tuple(self.ball), self.bar1_y[0], q_action2)
                    temp_q = self.Q.get(q_str2, 0.)
                    all_qa.append((temp_q, int(q_action2)))
                    #if temp_q > max_q:
                    #    max_q = temp_q
                    #    max_a = q_action2
                max_q = max(all_qa, key=lambda x:x[0])[0]
                max_a = max(all_qa, key=lambda x:x[0])[1]
                logging.debug("all_qa,%s",all_qa)
                logging.debug("max_q,%s",max_q)
                logging.debug("max_a,%s",max_a)
                #logging.debug("argmax_all_q",np.argmax(all_q))
                #logging.debug("max_a",max_a)
                #logging.debug("max_q",max_q)
                self.Q.update({q_str1: q_current + self.alpha * (q_reward + self.gamma * max_q - q_current)})
                # logging.debug("Q,\n%s", json.dumps(self.Q, indent=4))
                if random.random() > self.epsilon:
                    bar1_action = max_a
                else:
                    bar1_action = random.choice([-1, 0, 1])
                logging.debug("q_str1,%s", q_str1)
                logging.debug("max_q,%s", max_q)
                logging.debug("max_a,%s", max_a)
                logging.debug("max_a,%s", bar1_action)
            if self.is_curses:
                time.sleep(0.04)


def main():
    QLearningPingPong(is_curses=True, save_model=True)
    # QLearningPingPong(is_curses=True,qname="qout_good2.json",epsilon=0,save_model=False)


if __name__ == "__main__":
    main()
