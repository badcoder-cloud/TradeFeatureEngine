import numpy as np 
import pandas as pd 
import datetime


from utilis import booksflow_find_level, booksflow_compute_percent_variation, booksflow_manipulate_arrays, booksflow_datatrim, merge_suffixes

class booksflow():
    """
        Important notes: 
            Maintain consistency in current timestamp across all flows
            If the book is above book_ceil_thresh from the current price, it will be omited for the next reasons:
                - Computational efficiency
                - Who books so high if they want to trade now? Challange this statemant ...
            Aggregation explanation:  If the level_size is 20, books between [0-20) go to level 20, [20, 40) go to level 40, and so forth.
    """
    def __init__(self, exchange : str, symbol : str, insType : str, level_size : int, lookup : callable, book_ceil_thresh=5):
        """
            insType : spot, future, perpetual 
            level_size : the magnitude of the level to aggragate upon (measured in unites of the quote to base pair)
            book_ceil_thresh : % ceiling of price levels to ommit, default 5%
            lookup : a function to get formated timestamp,  bids and asks from a dictionary
        """
        # Identification
        self.exchange = exchange
        self.symbol = symbol
        self.insType = insType
        self.level_size = float(level_size)
        self.book_ceil_thresh = book_ceil_thresh
        self.df = pd.DataFrame()
        self.B = {"timestamp" : None, "bids" : {}, "asks" : {}}
        self.snapshot = None
        self.previous_second = -1
        self.current_second = 0
        self.price = 0

    
    def update_books(self, books):

        bids = self.lookup(books, "bids")
        asks, timestamp = self.lookup(books, "asks")

        self.B['timestamp'] = timestamp
        self.price = (bids[0][0] + asks[0][0]) / 2
         
        self.update_books_helper(bids, "bids")
        self.update_books_helper(asks, "asks")
        
        self.current_second = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').second

        if self.current_second > self.previous_second:
            self.dfs_input_books(current_price)
            self.previous_second = self.current_second
        if self.previous_second > self.current_second:
            self.df.replace(0, method='ffill', inplace=True)     
            self.df.replace(0, method='bfill', inplace=True)
            self.snapshot = self.df.copy()
            self.df = pd.DataFrame()
            self.previous_second = self.current_second
            # Delete unnecessary data
            booksflow_datatrim(current_price, self.B, 'bids', self.book_ceil_thresh)
            booksflow_datatrim(current_price, self.B, 'asks', self.book_ceil_thresh)
            # Start everything all over again
            self.dfs_input_books(current_price)

    def update_books_helper(self, books, side):
        """
          side: bids, asks
        """
        # Omit books above 5% from the current price
        for book in books:
            p = book[0]
            a = book[1]
            if abs(booksflow_compute_percent_variation(p, self.price)) > self.book_ceil_thresh:
                continue
            if a == 0:
                try:
                    del self.B[side][book[0]]
                except:
                    pass
            else:
                self.B[side][p] = a

    def dfs_input_books(self):
        """
            Inputs bids and asks into dfs
        """

        prices = np.array(list(map(float, self.B['bids'].keys())) + list(map(float, self.B['asks'].keys())), dtype=np.float16)
        amounts = np.array(list(map(float, self.B['bids'].values())) + list(map(float, self.B['asks'].values())), dtype=np.float16)
        levels = [booksflow_find_level(lev, self.level_size) for lev in  prices]
        unique_levels, inverse_indices = np.unique(levels, return_inverse=True)
        group_sums = np.bincount(inverse_indices, weights=amounts)
        columns = [str(col) for col in unique_levels]

        if self.df.empty:
            self.df = pd.DataFrame(0, index=list(range(60)), columns = columns)
            self.df.loc[self.current_second] = group_sums
            sorted_columns = sorted(map(float, self.df.columns))
            self.df = self.df[map(str, sorted_columns)]
        else:
            old_levels = np.array(self.df.columns)
            new_levels = np.setdiff1d(np.array(columns), old_levels)
            full_new_levels = np.concatenate((old_levels, np.setdiff1d(new_levels, old_levels))) 
            for l in new_levels:
                self.df[l] = 0
            sums = booksflow_manipulate_arrays(old_levels, full_new_levels, group_sums)
            self.df.loc[self.current_second] = sums
            sorted_columns = sorted(map(float, self.df.columns))
            self.df = self.df[map(str, sorted_columns)] 




class tradesflow():
    """
        Important notes: 
            Maintain consistency in the current timestamp across all flows
            Aggregation explanation:  If the level_size is 20, books between [0-20) go to level 20, [20, 40) go to level 40, and so forth.
    """

    def __init__(self, exchange : str, symbol : str, insType : str, level_size : int, lookup : callable):
        """
            insType : spot, future, perpetual 
            level_size : the magnitude of the level to aggragate upon (measured in unites of the quote to base pair)
            lookup : function to extract details from the response
        """
        self.exchange = exchange
        self.symbol = symbol
        self.insType = insType
        self.level_size = float(level_size)
        self.lookup = lookup
        self.buys = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.sells = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.snapshot_buys = None
        self.snapshot_sells = None
        self.snapshot_total = None
        self.snapshot_buys_dominance = None
        self.snapshot_sells_dominance = None
        self.previous_second = -1
        self.current_second = 0

    def dfs_input_trades(self, trade ):

        side, price, amount, timestamp = self.lookup(trade)
        self.current_second  =  datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').second

        if self.previous_second > current_second:

            self.snapshot_buys = self.buys.copy()
            self.snapshot.fillna(0, inplace = True)
            self.snapshot_sells = self.sells.copy()
            self.snapshot.fillna(0, inplace = True)
            
            self.snapshot_buys['price'].replace(0, method='ffill', inplace=True)
            self.snapshot_buys['price'].replace(0, method='bfill', inplace=True)
            self.snapshot_sells['price'].replace(0, method='ffill', inplace=True)
            self.snapshot_sells['price'].replace(0, method='bfill', inplace=True)

            self.snapshot_total = self.snapshot_buys.copy() + self.snapshot_sells.copy()
            self.snapshot_buys_dominance = self.snapshot_buys.copy() - self.snapshot_sells.copy()
            self.snapshot_dominance_buys.apply(lambda x: max(x, 0), inplace=True)
            self.snapshot_sells_dominance = self.snapshot_sells.copy() - self.snapshot_buys.copy()
            self.snapshot_dominance_buys.apply(lambda x: min(x, 0), inplace=True)
    
            self.buys = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
            self.sells = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))

        self.previous_second = self.current_second

        if side == 'buy':
            self.buys.loc[current_second, 'price'] = price
            level = booksflow_find_level(current_price, self.level_size)
            current_columns = (map(float, [x for x in self.buys.columns.tolist() if x != "price"]))
            if level not in current_columns:
                self.buys[str(level)] = 0
                self.buys.loc[current_second, str(level)] += amount
            else:
                self.buys.loc[current_second, str(level)] += amount

        
        if side == 'sell':
            self.sells.loc[current_second, 'price'] = price
            level = booksflow_find_level(current_price, self.level_size)
            current_columns = (map(float, [x for x in self.sells.columns.tolist() if x != "price"]))
            if level not in current_columns:
                self.sells[str(level)] = 0
                self.sells.loc[current_second, str(level)] += amount
            else:
                self.sells.loc[current_second, str(level)] += amount






class oiflow():
    """
        Important notes: 
            Maintain consistency in the current timestamp across all flows
            Aggregation explanation:  If the level_size is 20, books between [0-20) go to level 20, [20, 40) go to level 40, and so forth.
    """

    def __init__(self, exchange : str, symbol : str, insType : str, level_size : int, lookup : callable):
        """
            insType : spot, future, perpetual 
            level_size : the magnitude of the level to aggragate upon (measured in unites of the quote to base pair
            lookup : a function that returns formated oi with timestamp from response
        """
        self.exchange = exchange
        self.symbol = symbol
        self.insType = insType
        self.level_size = float(level_size)
        self.lookup = lookup
        self.raw_data = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.snapshot = None
        self.previous_second = -1
        self.current_second = 0
        self.previous_oi = None

    def dfs_input_oi(self, tick):
        
        oi, price, timestamp = self.lookup(tick)
        self.current_second = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').second 


        if self.previous_oi == None:
            self.previous_oi = oi

        amount = oi - self.previous_oi

        if self.previous_second > current_second:
            self.snapshot = self.raw_data.copy()
            self.snapshot.fillna(0, inplace = True)
            self.snapshot['price'].replace(0, method='ffill', inplace=True)
            self.snapshot['price'].replace(0, method='bfill', inplace=True)
            self.raw_data = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.previous_second = self.current_second
        self.raw_data.loc[current_second, 'price'] = price
        level = booksflow_find_level(price, self.level_size)
        current_columns = (map(float, [x for x in self.raw_data.columns.tolist() if x != "price"]))
        if level not in current_columns:
            self.raw_data[str(level)] = 0
            self.raw_data.loc[current_second, str(level)] = amount
        else:
            self.raw_data.loc[current_second, str(level)] = amount

        self.previous_oi = oi




class liquidationsflow():
    """
        Important notes: 
            Maintain consistency in the current timestamp across all flows
            Aggregation explanation:  If the level_size is 20, books between [0-20) go to level 20, [20, 40) go to level 40, and so forth.
    """

    def __init__(self, exchange : str, symbol : str, insType : str, level_size : int, lookup : callable):
        """
            insType : spot, future, perpetual 
            level_size : the magnitude of the level to aggragate upon (measured in unites of the quote to base pair)
        """
        self.exchange = exchange
        self.symbol = symbol
        self.insType = insType
        self.level_size = float(level_size)
        self.lookup = lookup
        self.longs = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.shorts = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        self.snapshot_longs = None
        self.snapshot_shorts = None
        self.snapshot_total = None
        self.previous_second = -1
        self.current_second = 0

    def dfs_input_liquidations(self, tick):

        side, price, amount, timestamp = lookup(tick)

        current_second = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').second

        if self.previous_second > current_second:

            self.snapshot_longs = self.longs.copy()
            self.snapshot_shorts = self.longs.copy()
            self.snapshot_total = self.longs.copy() + self.shorts.copy()
            
            self.snapshot_longs.fillna(0, inplace = True)
            self.snapshot_shorts.fillna(0, inplace = True)
            
            self.snapshot_longs['price'].replace(0, method='ffill', inplace=True)
            self.snapshot_longs['price'].replace(0, method='bfill', inplace=True)
            self.snapshot_shorts['price'].replace(0, method='ffill', inplace=True)
            self.snapshot_shorts['price'].replace(0, method='bfill', inplace=True)

            self.longs = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
            self.shorts = pd.DataFrame(0, index=list(range(0, 60, 1)) , columns=np.array(['price']))
        
        self.previous_second = self.current_second

        if side == "buy":
            self.longs.loc[current_second, 'price'] = price
            level = booksflow_find_level(price, self.level_size)
            current_columns = (map(float, [x for x in self.longs.columns.tolist() if x != "price"]))
            if level not in current_columns:
                self.longs[str(level)] = 0
                self.longs.loc[current_second, str(level)] += amount
            else:
                self.longs.loc[current_second, str(level)] += amount

        if side == "sell":
            self.shorts.loc[current_second, 'price'] = price
            level = booksflow_find_level(price, self.level_size)
            current_columns = (map(float, [x for x in self.shorts.columns.tolist() if x != "price"]))
            if level not in current_columns:
                self.shorts[str(level)] = 0
                self.shorts.loc[current_second, str(level)] += amount
            else:
                self.shorts.loc[current_second, str(level)] += amount



def build_option_dataframes(expiration_ranges, columns):
    df_dic = {}
    for i, exp_range in enumerate(expiration_ranges):
        if i in [0, len(expiration_ranges)-1]:
            df_dic[f'{int(exp_range)}'] = pd.DataFrame(columns=columns) #.set_index('timestamp')
            df_dic[f'{int(exp_range)}']['timestamp'] = pd.to_datetime([])
            df_dic[f'{int(exp_range)}'].set_index('timestamp', inplace=True)
        if i in [len(expiration_ranges)-1]:
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}'] = pd.DataFrame(columns=columns) #.set_index('timestamp')
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}']['timestamp'] = pd.to_datetime([])
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}'].set_index('timestamp', inplace=True)
        else:
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}'] = pd.DataFrame(columns=columns) #.set_index('timestamp')
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}']['timestamp'] = pd.to_datetime([])
            df_dic[f'{int(expiration_ranges[i-1])}_{int(exp_range)}'].set_index('timestamp', inplace=True)
    df_dic.pop(f"{int(np.max(expiration_ranges))}_{int(np.min(expiration_ranges))}")
    return df_dic


def oiflowOption_getcolumns(price_percentage_ranges: np.array):
    price_percentage_ranges = np.unique(np.sort(np.concatenate((price_percentage_ranges, -price_percentage_ranges)), axis=0))
    price_percentage_ranges[price_percentage_ranges == -0] = 0
    price_percentage_ranges[price_percentage_ranges == price_percentage_ranges[0]] = 0
    price_percentage_ranges = np.unique(price_percentage_ranges)
    columns = np.concatenate((np.array(['timestamp']), price_percentage_ranges), axis=0)
    return column


def oiflowOption_getranges(price_percentage_ranges: np.array):
    price_percentage_ranges = np.unique(np.sort(np.concatenate((price_percentage_ranges, -price_percentage_ranges)), axis=0))
    price_percentage_ranges[price_percentage_ranges == -0] = 0
    price_percentage_ranges[price_percentage_ranges == price_percentage_ranges[0]] = 0
    price_percentage_ranges = np.unique(price_percentage_ranges)
    return price_percentage_ranges


def oiflowOption_dictionary_helper(countdown_ranges, countdowns):
    countdown_ranges_flt = sorted(list(set(([float(item) for sublist in [x.split('_') for x in countdown_ranges] for item in sublist]))))
    mx = max(countdown_ranges_flt)
    mn = min(countdown_ranges_flt)
    l = {key: [] for key in countdown_ranges}
    for index, cf in enumerate(countdown_ranges_flt):
      for v in countdowns.tolist():
          if cf == mn and v <= cf:
              l[str(int(cf))].append(v)
          if cf != mn and v <= cf and v > countdown_ranges_flt[index-1]:
              l[f"{str(int(countdown_ranges_flt[index-1]))}_{str(int(cf))}"].append(v)
          if cf == mx and v > cf:
              l[str(int(cf))].append(v)
    return l

def oiflowOption_pcd(center, value):
    if center == 0 and value > center:
        return float(100)
    if value == 0 and value < center:
        return float(9999999999)
    else:
        diff = value - center
        average = (center + value) / 2
        percentage_diff = (diff / average) * 100
        return percentage_diff

def oiflowOption_choose_range(ppr, value):
    for index, r in enumerate(ppr):
        if index == 0 and value < r:
            return ppr[0]
        if index == len(ppr)-1 and value > r:
            return ppr[-1]
        if value < r and value >= ppr[index-1]:
            return r

class oiflowOption():

    def __init__ (self, exchange : str, instrument : str, ranges : np.array,  expiry_windows : np.array, lookup : callable):

        """
            The main objects of the class are  self.df_call self.df_put that contain 
            dictionaries of dataframes of OIs by strices by expiration ranges of puts and calls options
            ranges : ranges of % difference of the strike price from current price
            expiry_windows :  is used to create heatmaps of OI per strike per expiration limit.
                                 np.array([1.0, 7.0, 35.0]) will create 4 expiration ranges 
                                    - (0 , 1]
                                    - (1 , 7]
                                    - (7, 35]
                                    - (35, +inf)
            lookup : A function to access dictionary elements that returns 3 lists with the same length:
                    - strikes
                    - expirations
                    - open interest
                    where each index corresponds to strake, expiration countdown and open interest for the same instrument
        """
        self.exchange = exchange
        self.instrument = instrument
        self.lookup = lookup
        self.ranges = ranges
        self.expiry_windows = expiry_windows
        self.df_call = {}
        self.df_put = {}

    def input_oi(self, data : json):

        self.input_oi_helper(data=data, side="C", df_side = self.df_call)
        self.input_oi_helper(data=data, side="P", df_side = self.df_put)



    def input_oi_helper(self, data : dict, side : str, df_side):
        
        strikes, countdowns, oi, timestamp = self.lookup(data, side)

        options_data = {"strikes" : strikes, "countdown" :countdowns, "oi" : oi}

        df = pd.DataFrame(options_data).groupby(['countdown', 'strikes']).sum().reset_index()
        df = df[(df != 0).all(axis=1)]

        if side == "C":
            self.df_call = build_option_dataframes(self.expiry_windows, columns=oiflowOption_getcolumns(ranges)) 
        if side == "P": 
            self.df_put = build_option_dataframes(self.expiry_windows, columns=oiflowOption_getcolumns(ranges)) 

        helper = oiflowOption_dictionary_helper(list(df_side.keys()), countdowns.unique())
        ranges = oiflowOption_getranges(expiry_windows)

        for dfid in helper.keys():
            empty_df = pd.DataFrame()
            for countdown in helper[dfid]:
                d = df[df['countdown'] == countdown ].drop(columns=['countdown'])
                d['pcd'] = df['strikes'].apply(lambda x : oiflowOption_pcd(indexPrice, x))
                d['range'] = d['pcd'].apply(lambda x: oiflowOption_choose_range(ranges, x))
                d = d.groupby(['range']).sum().reset_index().drop(columns=["strikes", "pcd"]).set_index('range')
                missing_values = np.setdiff1d(ranges, d.index.values)
                new_rows = pd.DataFrame({'oi': 0}, index=missing_values)
                combined_df = pd.concat([d, new_rows])
                combined_df = combined_df.transpose() 
                combined_df['timestamp'] = pd.to_datetime(timestamp)
                combined_df.set_index('timestamp', inplace=True)
                combined_df = combined_df.sort_index(axis=1)
                empty_df = pd.concat([empty_df, combined_df], ignore_index=True)
            df_side[dfid].loc[pd.to_datetime(timestamp)]  = empty_df.sum(axis=0).values.T
            df_side[dfid] = df_side[dfid].tail(1)
        
        
class voidflow():
    """
        Gathers statistical information on canceled limit order books in the form of a heatmap variance over 60 second history
        return pd.Dataframe with columns indicating levels. df contains only 1 row
    """
    def __init__ (self, instrument : str, insType : str, axis : dict):
        """
            axis : A dictionary that encapsulates a collection of flows originating from diverse exchanges in the key "books
                   and the collection of trades origination from different exchanges in the key "trades"
                   Each key contains the corresponding 60 second pd.Dataframes of heatmap data
                   should be:
                   {
                      books : classbooks.merge.object
                      trades : classtrades.merge.object
                   }
                   snapshot_voids    : total closed orders per timestamp,  
                                       closed orders heatmap per level, 
                   snapshot_voidsvar : total variance of closed orders
                                       heatmap of variances of closed orders per level
        """
        self.instrument = instrument
        self.insType = insType
        self.axis = axis
        self.snapshot_voids = pd.DataFrame()
        self.snapshot_voidsvar = pd.DataFrame()

    def get_voids(self, current_price):

        
        df_books = self.axis['books'].snapshot.copy()
        df_trades = self.axis['trades'].snapshot.copy()
        merged_df = pd.merge(df_books, df_trades, how='outer', left_index=True, right_index=True, suffixes=('_books', '_trades'))
        common_columns = df_books.columns.intersection(df_trades.columns).tolist()
        
        for column in common_columns:
            if "price" not in column:
                merged_df[column] = merged_df[column + '_books'].sub(merged_df[column + '_trades'], fill_value=0)
                merged_df = merged_df.drop([column + '_books', column + '_trades'], axis=1)
        merged_df = merged_df.drop('price_books', axis=1)
        merged_df = merged_df.rename(columns={'price_trades': 'price'})

        sorted_columns = sorted(map(float, [c for c in merged_df.columns if "price" not in c]))
        merged_df = merged_df[map(str, ['price'] + sorted_columns)] 

        for index in range(len(merged_df)):
            if index != 0:
                merged_df.iloc[index-1] = merged_df.iloc[index].values - merged_df.iloc[index-1].values

        price = merged_df['price'].values[-1]
        self.snapshot_voids = merged_df.drop(columns=['price']).sum(axis=0).T
        snapshot_voids_columns = ["_".join([x.split('.')[0], "void_volume"]) for x in merged_df.columns.tolist()]
        self.snapshot_voids = self.snapshot_voids.rename(columns=dict(zip(self.snapshot_voids.columns, snapshot_voids_columns)))
        total_closed = merged_df.sum(axis=0).sum().values[0]
        self.snapshot_voids.insert(0, 'price', [price])
        self.snapshot_voids.insert(0, 'void_volume', [total_closed])

        self.snapshot_voidsvar = merged_df.var().T
        snapshot_voids_columns = ["_".join([x.split('.')[0], "voidvar_volume"]) for x in merged_df.columns.tolist()]
        self.snapshot_voidsvar = self.snapshot_voids.rename(columns=dict(zip(self.snapshot_voids.columns, snapshot_voids_columns)))
        total_variance = self.snapshot_voidsvar.var().sum().values[0]
        self.snapshot_voids.insert(0, 'price', [price])
        self.snapshot_voidsvar.insert(0, 'voidvar_volume', [total_variance])
        
    