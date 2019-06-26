#!/usr/bin/env python
#
# This piece of code helps to build tpo market profile chart from 1 min candles  : you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright sivamgr@gmail.com

from datetime import datetime
import statistics
import math
import re

class tpo_window:
    def __init__(self):
        self.tick_size = 0
        self.tpo = dict()
        self.initial_balance_hi = 0
        self.initial_balance_lo = 0
        self.initial_balance_range = 0
        self.TPO_count = 0
        self.VA_TPO_count = 0
        self.POC_TPO_count = 0
        self.VAL = 0
        self.VAH = 0
        self.POC = 0
        self.single_print_lo_count = 0
        self.single_print_hi_count = 0
        self.range = 0
        self.range_hi = 0
        self.range_lo = 0
        self.datestamp = None
        self.day_starttime = None
        self.open = 0
        self.close = 0
        self.tpo_added_in_last_update = 0
        self.tpo_last_changed_timestamp = None
        self.current_letter = 'A'
    def letter(self, dt):
        #30 mins per session
        codes = 'ABCDEFGHIJKLMNPQRSTUVWXYZ'
        idx = int( (dt - self.day_starttime).total_seconds() / (30 * 60))
        if(idx < len(codes)):
            return codes[int( (dt - self.day_starttime).total_seconds() / (30 * 60))]
        return 'Z'

    def set_tick_size(self, p):
        #buckets = [[100, 0.1], [200, 0.2], [500, 0.5], [1000, 1], [2000, 2], [5000, 5], [10000, 10]]
        #buckets = [[100, 0.2], [200, 0.5], [500, 1], [1000, 2], [2000, 5], [5000, 10], [10000, 20]]
        buckets = [[50, 0.25],[100, 0.5], [200, 1], [500, 2], [1000, 5], [2000, 10], [5000, 20], [10000, 50]]
        self.tick_size = 0.10
        for b in buckets:
            if(p < b[0]):
                break
            self.tick_size = b[1]

    def setup(self, dt, o, h, l, c):
        self.set_tick_size(h)
        self.day_starttime = dt
        self.initial_balance_hi = h
        self.initial_balance_lo = l
        self.open = o
        self.close = c
        self.datestamp = dt.date()

    def bucket(self, p):
        return round( p / self.tick_size) * self.tick_size

    def bucket_next(self, p):
        return self.bucket(p + self.tick_size)

    def bucket_prev(self, p):
        return self.bucket(p - self.tick_size)

    def update(self, dt, o, h, l, c):
        if(o > h): h = o
        if(o < l): l = o
        if(c > h): h = c
        if(c < l): l = c
        
        if(self.tick_size == 0):
            if(h > 0):
                self.setup(dt, o, h, l, c)
            else:
                return

        self.close = c
        alp = self.letter(dt)
        self.current_letter = alp
        rprice = self.bucket(l)
        self.tpo_added_in_last_update = 0
        while rprice <= h:
            #print(str(self.tick_size) + ' ' + str(h) + ' ' + str(rprice))
            if(rprice in self.tpo):
                if(alp not in self.tpo[rprice]):
                    self.tpo[rprice] += alp
                    self.tpo_added_in_last_update += 1
            else:
                self.tpo[rprice] = alp
                self.tpo_added_in_last_update += 1
            rprice = self.bucket_next(rprice)

        #return if no change in TPO
        if(self.tpo_added_in_last_update == 0):
            return

        #total tpo
        self.TPO_count += self.tpo_added_in_last_update
        self.tpo_last_changed_timestamp = dt
        tpo_rprices = sorted(self.tpo.keys())

        #range update
        self.range_lo = tpo_rprices[0]
        self.range_hi = tpo_rprices[-1]
        self.range = self.range_hi - self.range_lo

        #initial balance
        if(alp < 'C'):
            self.initial_balance_lo = self.range_lo
            self.initial_balance_hi = self.range_hi
            self.initial_balance_range = self.range

        #Find POC
        median_price = self.bucket(statistics.median( tpo_rprices ))
        while(median_price not in self.tpo):
            median_price = self.bucket_prev(median_price)
        poc = median_price
        it_rprice_hi = median_price
        it_rprice_lo = median_price
        while (it_rprice_hi <= self.range_hi) or (it_rprice_lo >= self.range_lo):
            if (it_rprice_hi in self.tpo):
                if(len(self.tpo[poc]) < len(self.tpo[it_rprice_hi])):
                    poc = it_rprice_hi
            if (it_rprice_lo in self.tpo):
                if(len(self.tpo[poc]) < len(self.tpo[it_rprice_lo])):
                    poc = it_rprice_lo
            it_rprice_lo = self.bucket_prev(it_rprice_lo)
            it_rprice_hi = self.bucket_next(it_rprice_hi)
        self.POC = poc
        self.POC_TPO_count = len(self.tpo[poc])
        #value area
        tpo70pc = int(0.70 * self.TPO_count)
        varea_total_tpo = self.POC_TPO_count
        varea_hi = poc
        varea_lo = poc
        varea_hi_next = self.bucket_next(poc)
        varea_lo_next = self.bucket_prev(poc)
        while(varea_total_tpo < tpo70pc):
            is_higher_exist =  (varea_hi_next in self.tpo)
            is_lower_exist  =  (varea_lo_next in self.tpo)
            pick_lower_varea = True
            if(is_higher_exist and is_lower_exist):
                if(len(self.tpo[varea_hi_next]) >= len(self.tpo[varea_lo_next])):
                    pick_lower_varea = False
            elif(is_higher_exist):
                pick_lower_varea = False
            else:
                break

            if(pick_lower_varea):
                varea_lo = varea_lo_next
                varea_lo_next = self.bucket_prev(varea_lo)
                varea_total_tpo += len(self.tpo[varea_lo])
            else:
                varea_hi = varea_hi_next
                varea_hi_next = self.bucket_next(varea_hi)
                varea_total_tpo += len(self.tpo[varea_hi])

        self.VAH = varea_hi
        self.VAL = varea_lo
        self.VA_TPO_count = varea_total_tpo
        #rotation-factor - TBD

        #buy/sell tail length
        self.single_print_lo_count = 0
        for rprice in tpo_rprices:
            if(len(self.tpo[rprice]) > 1):
                break
            self.single_print_lo_count += 1
        self.single_print_hi_count = 0
        for rprice in reversed(tpo_rprices):
            if(len(self.tpo[rprice]) > 1):
                break
            self.single_print_hi_count += 1

    def print_tick(self, rprice):
        return ( ('O' if (rprice == self.bucket(self.open))  else ' ')  +   (self.tpo[rprice] if rprice in self.tpo else '')  +  ('#' if (rprice == self.bucket(self.close))  else ''))

    def get_tpo_count(self, rprice):
        return len(self.tpo[rprice]) if rprice in self.tpo else 0

    def print(self):
        print("%s | %s | TPO %u | Range %.2f | IB-Range %.2f [%.2f - %.2f] | HI %.2f | VAH %.2f | POC %.2f | VAL %.2f | LO %.2f" % 
            (
                self.tpo_last_changed_timestamp.strftime('%Y-%m-%d %H:%M:%S'),  
                self.letter(self.tpo_last_changed_timestamp),
                self.TPO_count,
                self.range,
                self.initial_balance_range,
                self.initial_balance_lo,
                self.initial_balance_hi,
                self.range_hi,
                self.VAH,
                self.POC,
                self.VAL,
                self.range_lo
            ) )


class tpo_profile:
    def __init__(self, max_days=5):
        self.tp = []
        self.max_days = max_days
        self.nrprices = 0
        self.rprice_mean = 0
        self.rprice_stddev = 0
        self.range_hi = 0
        self.range_lo = 0
        
    def get_tpo_count(self, rprice):
        ntick = 0
        for i in range(0, len(self.tp)):
            ntick += self.tp[i].get_tpo_count(rprice)
        return ntick

    def update(self, dt, o, h, l, c):
        if (len(self.tp) == 0) or (self.tp[0].datestamp != dt.date()):
            self.tp.insert(0,tpo_window())
            if(len(self.tp) > self.max_days):
                del self.tp[-1]
        self.tp[0].update(dt, o, h, l, c)
        if(self.tp[0].tpo_added_in_last_update > 0):
            self.update_profile()

    def update_profile(self):
        self.range_lo = min([tp.range_lo for tp in self.tp])
        if(self.range_lo <=0):
            print([tp.datestamp for tp in self.tp])  
            print([tp.range_lo for tp in self.tp])
            print([tp.range_hi for tp in self.tp])
        self.range_hi = max([tp.range_hi for tp in self.tp])
        total_tpo = 0
        sum_tpo_price = 0
        rprice = self.range_hi
        tpos = []
        while(rprice >= self.range_lo):
            tpo = 0
            for i in range(len(self.tp)-1, -1, -1):
                line = self.tp[i].print_tick(rprice)
                tpo += len(re.sub('[^A-N]','',line))
            total_tpo += tpo
            sum_tpo_price += tpo * rprice
            tpos.append((rprice, tpo))
            rprice = self.tp[0].bucket_prev(rprice)

        self.rprice_mean = sum_tpo_price / total_tpo

        sumdiffsqr = 0
        for t in tpos:
            diffmean = (t[0] - self.rprice_mean)
            sumdiffsqr += diffmean * diffmean * t[1]
        self.rprice_stddev = math.sqrt( sumdiffsqr/total_tpo )

    def print(self):
        print("10Day Mean : %.2f, Stdev : %.2f, [Hi : %.2f, Lo : %.2f, Range : %.2f ] [%u]" % 
            (
                self.rprice_mean,  
                self.rprice_stddev,
                self.range_hi,
                self.range_lo,
                (self.range_hi - self.range_lo)*100.0/self.range_lo,
                self.nrprices        
            ) )

    def print_plot(self, bemptyend=True):
        daycode = 'MTWTFSS'
        range_lo = min([tp.range_lo for tp in self.tp])
        rprice = max([tp.range_hi for tp in self.tp])
        #os.system('cls' if os.name == 'nt' else 'clear')
        print(' '.ljust(205))
        nrprices = 0
        while(rprice >= range_lo):
            line = '{0:.2f}'.format(rprice)
            for i in range(len(self.tp)-1, -1, -1):
                bar = self.tp[i].print_tick(rprice)
                line += bar.ljust(15)
            #line +=  str(len(re.sub('[^A-N]','',line))).ljust(4)
            line +=  '%.50s' % (re.sub('[A-N]','*',re.sub('[^A-N]','',line)).ljust(50))
            print(line) 
            rprice = self.tp[0].bucket_prev(rprice)
            nrprices += 1
            if(nrprices > 40):
                break
        line = ' '.ljust(5)
        for i in range(len(self.tp)-1, -1, -1):
            bar = str(self.tp[i].datestamp) + ' ' +daycode[self.tp[i].datestamp.weekday()] 
            line += bar.ljust(15)
        print(line)

        # clear old lines
        if(bemptyend):
            while(self.nrprices > nrprices):
                print(''.ljust(205))
                self.nrprices -= 1
        self.nrprices = nrprices
        
'''
Sample usae below
class TimeProfileTest():
    def __init__(self):
        self.tpo = tpo_profile(max_days=10)
 
    def update(dt, o, h, l, c):
        self.tpo.update(dt, o, h, l, c)
        
'''