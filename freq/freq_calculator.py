# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 09:53:53 2015
@author: Juan Chacon-Hurtado @ unesco-ihe 
email - j.chaconhurtado@unesco-ihe.org

FREQ Library

Contains the modules for monitoring of groundwater networks

------------
V 0.0 - Implementation in single file of complete FREQ library.

"""
import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sts


MIN_SAMPLES = 40


class CalculatorSampleAmountError(Exception):
    pass

def load(data=None, data_path=None, init_date=None, end_date=None, 
         frequency='M', interpolation_method='linear', delimiter=';'):
    '''
    Load and interpolate the data to be used in the freq model
    
    Parameters
    ----------
    
    data : pd DataFrame
        Dataframe object with dates as index
    data_path : str
        Path where the csv data is located. Field for dates are named as 
        timestamp and data as value.
    init_date : str
        String representing the desired initial data for the analysis. If None,
        this will be the first record
    end_date : str
        String representing the desired final data for the analysis. If None,
        this will be the last record
    frequency : str
        Frequency in which the data is to be generated.
    interpolation_method : str
        method used for the interpolation of values between observations
    delimiter : str
        delimiter used in the csv file to separate the fields
        
    Returns
    -------
    
    data_out : pd DataFrame
        Dataframe interpolated at the requested frequency
    data_mod : nd_array
        Field of values corresponding at the output dataframe
    '''
    
    if data is None:
        if data_path is None:
            data = pd.read_csv('../../FREQ_code/freq-nov-30/testing_data/001.csv',
                               parse_dates=['timestamp'], 
                               index_col='timestamp', sep=delimiter)
        else:
            data = pd.read_csv(data_path, parse_dates=['timestamp'], 
                               index_col='timestamp', sep=delimiter)
        ## Resampling into average monthly values
        data = data.value

    if init_date is None:
        init_date = data.index[0]
    
    if end_date is None:
        end_date = data.index[-1]
        
    data_out = data.resample(frequency, 'mean').interpolate(
                             method=interpolation_method)[init_date:end_date]
    data_mod = np.array(data_out)
    
    return data_out, data_mod


def step(data, bp, alpha, detrend_anyway=True):
    '''
    Calculates and remove step trend
    
    Parameters
    ----------
    data : array_like
        Time serries for which the step trend is to be removed
    bp : int
        Step in which the series is going to split. If zero is selected, means
        no trend selection, and only centering the data.
    alpha : float
        significance of the t-test for changes in the mean (0-1)
    detrend_anyway : bool
        Perform the detrend, even if the difference in the means is not 
        significant
    
    Returns
    -------
    det_serie : nd_array
        Time series in which the resulting serie is detrended
    trend : nd_array
        Trend that was removed from the origincal serie
    param : list
        List containing the regression parameters as: mean_a, mean_b, pval, 
        t_test_val
    text_output : str
        Textual explaination of the results
        
    '''
    # Input validation
    if alpha > 1.0 or alpha < 0.0:
        raise ValueError('Alpha value has to be between 0 and 1')
    if not isinstance(bp, int):
        raise ValueError('The breaking point has to be an integer')
    if bp < 0 or bp > len(data):
        raise ValueError('The breaking point has to be between 0 and {0}'\
                        .format(len(data)))
    if not isinstance(detrend_anyway, bool):
        raise ValueError('detrend_anyway has to be boolean')
    if len(data) < MIN_SAMPLES:
        raise CalculatorSampleAmountError(
            'Too little data, dataset has to be larger than {0}'.format(
                MIN_SAMPLES))
    
    if bp == 0:
        # In case no trend is selected
        mean_a = np.average(data)
        mean_b = mean_a
        
        pval = ERROR_CODE
        t_test_val = ERROR_CODE
        text_output = 'No trend was selected'
        trend = mean_a*np.ones(len(data))
        det_serie = np.array(data) - mean_a
        
    else:
    
        # get means before (a) and after (b) the breaking point
        mean_a = np.average(data[:bp])
        mean_b = np.average(data[bp:])
        
        #Trend
        trend = np.concatenate((mean_a*np.ones(bp),
                                   mean_b*np.ones(len(data)-bp)))     
        
        ## make t test
        t_test_val, pval = st.ttest_ind(data[:bp],data[bp:])
        
        det_serie = np.concatenate((data[:bp] - np.average(data[:bp]),
                                      data[bp:] - np.average(data[bp:])))     
        
        # Using the t-test
        if alpha <= pval:
            text_output = 'There is no significant difference at a {0} \
                           level of confidence\np-value = {1}\nt-test value \
                           {2}'.format(alpha, pval, t_test_val)
            if not detrend_anyway:
                det_serie = data
        else:
            text_output = 'There is a significant difference at a {0} level \
                           of confidence\np-value = {1}\nt-test value \
                           {2}'.format(alpha, pval, t_test_val)
       
    param = mean_a, mean_b, pval, t_test_val        
    
    return det_serie, trend, param, text_output


def linear(data, alpha, detrend_anyway=True):
    '''
    Calculates and remove step trend
    
    Parameters
    ----------
    data : array_like
        Time serries for which the step trend is to be removed
    alpha : float
        significance of the t-test for linear trend (0-1)
    detrend_anyway : bool
        Perform the detrend, even if the difference in the means is not 
        significant
    
    Returns
    -------
    det_serie : nd_array
        Time series in which the resulting serie is detrended
    trend : nd_array
        Trend that was removed from the origincal serie
    param : list
        List containing the regression parameters as: a, b, r, pval, t_test_val
    text_output : str
        Textual explaination of the results
    '''
    # Input validation
    if alpha > 1.0 or alpha < 0.0:
        raise ValueError('Alpha value has to be between 0 and 1')
    if not isinstance(detrend_anyway, bool):
        raise ValueError('detrend_anyway has to be boolean')
    if len(data) < MIN_SAMPLES:
        raise CalculatorSampleAmountError(
            'Too little data, dataset has to be larger than {0}'\
                        .format(MIN_SAMPLES))
                        
    ## Make linear regression
    x_values = np.array(range(len(data)))
    a, b, r, pval, err = st.linregress(x_values, data)
    trend = a*x_values + b
    
    ## t-test for mean
    det_serie = data - trend
    t_test_val, pval = st.ttest_ind(det_serie, data)
    
    # Using the t-test
    if alpha <= pval:
        text_output = 'There is no significant difference at a {0} level of \
                       confidence\np-value = {1}\nt-test value {2}'.format(
                                                       alpha, pval, t_test_val)
        if not detrend_anyway:
            det_serie = data
    else:
        text_output = 'There is a significant difference at a {0} level of \
                       confidence\np-value = {1}\nt-test value {2}'.format(
                                                       alpha, pval, t_test_val)
    
    param = a, b, r, pval, t_test_val
    return det_serie, trend, param, text_output


def correlogram(data, n_lags):
    '''
    Calculates the correlogram function
    
    Parameters
    ----------
    data : array_like
        Time series for which the step trend is to be removed
    n_lags : int
        Number of lags used for the correlogram computation
    
    Returns
    -------
    corr_vec : nd_array
        Vector with correlogram function
    '''
    # Input validation
    if len(data) < MIN_SAMPLES:
        raise CalculatorSampleAmountError(
            'Too little data ({0}), dataset has to be larger than '
                        '{1}'.format(len(data), MIN_SAMPLES))
    if not isinstance(n_lags, int) or n_lags < 0:
        raise ValueError('n_lags has to be a positive integer')
        
    z = np.zeros((len(data)-n_lags+1, n_lags))
    for i in range(n_lags):
        z[:,i] = data[i:len(data) - n_lags + 1 + i]
    
    corr_vec = np.corrcoef(z, rowvar=0)[0, :]
    return corr_vec


def harmonic(data, n_harmonics):
    '''
    Calculates and remove the harmonic trend
    
    Parameters
    ----------
    data : array_like
        Time serries for which the step trend is to be removed
    n_harmonics : int
        Number of harmonics to be removed from the series
    
    Returns
    -------
    det_serie : nd_array
        Time series in which the resulting serie is detrended
    trend : nd_array
        Trend that was removed from the original serie
    param : list
        List containing the regression parameters as: a_param, b_param, 
        sigma_param
    ac_ps : nd_array
        Accumulated power spectrum
    '''
    # Input validation
    if len(data) < MIN_SAMPLES:
        raise CalculatorSampleAmountError(
            'Too little data ({0}), dataset has to be larger than '
                        '{1}'.format(len(data), MIN_SAMPLES))
                        
    if not isinstance(n_harmonics, int) or n_harmonics < 0:
        raise ValueError('n_harmonics has to be a positive integer')
    
    if n_harmonics > len(data)/2:
        raise ValueError('Too many harmonics, maximum number of harmonics is \
                        {0}'.format(int(len(data)/2)))
    
    data = data - np.mean(data)
    x_values = np.array(range(len(data)))
    fft_vec = np.fft.fft(data)
    af = np.real(fft_vec)/len(data)
    bf = np.imag(fft_vec)/len(data)
    ps = 2.0*(np.power(af,2)/2.0 + np.power(bf,2)/2.0)
    ps = ps[:len(data)/2]
    ps[-1] = ps[-1]/2.0
    ps2 = ps/np.max(np.cumsum(ps))
    ac_ps = np.cumsum(ps2)
    #VC = ps/(2*Sa**2)
    #IF = heapq.nlargest(n_harmonics,ps)
    
    i_indx = ps.argsort()
    i_indx = i_indx[::-1]
    
    trend = np.zeros(len(data))
    a_param = []
    b_param = []
    sigma_param = []
    for i in range(n_harmonics):
        NewPeriod = af[i_indx[i]]*np.cos(2*np.pi*(i_indx[i])*x_values/len(data))\
                    + bf[i_indx[i]]*np.sin(2*np.pi*i_indx[i]*x_values/len(data))
        trend = trend + NewPeriod
        a_param.append(af[i_indx[i]])
        b_param.append(bf[i_indx[i]])
        sigma_param.append(ps[i_indx[i]])
        
    
    det_serie = data - trend
    param = a_param, b_param, sigma_param
    
    det_serie = np.array(det_serie)
    x_ac_ps = len(ac_ps)/np.array(range(1, len(ac_ps) + 1))
    
    return det_serie, trend, param, ac_ps, x_ac_ps


def autoregressive(data, per):
    '''
    Calculates and remove step trend
    
    Parameters
    ----------
    data : array_like
        Time series for which the step trend is to be removed
    per : int
        Number of periods used in the training of the autoregressive model
    
    Returns
    -------
    det_serie : nd_array
        Time series in which the resulting serie is detrended
    trend : nd_array
        Trend that was removed from the original serie
    param : list
        Object containing the autoregressive model parameters
    aic_model : float
         Akaike Information Criterion of the autoregressive model
    std_error : float
         Standard deviation of the innovation (error) term
    '''    
    # Input validation
    if len(data) < MIN_SAMPLES:
        raise CalculatorSampleAmountError(
            'Too little data ({0}), dataset has to be larger than '
                        '{1}'.format(len(data), MIN_SAMPLES))
                        
    if not isinstance(per, int) or per < 0:
        raise ValueError('n_harmonics has to be a positive integer')
    
    if per > 0.3*len(data):
        raise ValueError('Too many periods, maximum number of periods is '
                         '{0}'.format(int(0.3*len(data))))
                        
    ar_model = sts.tsa.AR(data).fit(per)
    aic_model = ar_model.aic
    std_error = np.sqrt(ar_model.sigma2)
    
    #Model Run
    trend = np.zeros(len(data))
    trend[:per-1] = np.average(data)
    trend[per-1:] = ar_model.predict(per,len(data))
    
    #Detrended serie
    det_serie = data - trend    
    
    #Parameter vector
    param = ar_model.params
    
    return det_serie, trend, param, aic_model, std_error


def test():
    samp_files = ['../../FREQ_code/freq-nov-30/testing_data/001.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/002.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/003.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/004.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/005.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/006.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/007.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/008.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/009.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/010.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/011.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/012.csv',
                  '../../FREQ_code/freq-nov-30/testing_data/013.csv',]
    
    for samp_file in samp_files:
        try:
            error_field = 'Error in load'
            data = load(data_path=samp_file)[1]

            error_field = 'Error in step'        
            step_t = step(data, bp=10, alpha=0.05, detrend_anyway=True)[0]

            error_field = 'Error in linear'            
            linear_t = linear(step_t, alpha=0.05, detrend_anyway=True)[0]

            error_field = 'Error in correlogram'            
            correlogram(linear_t, n_lags=2)

            error_field = 'Error in harmonic'
            harmonic_t = harmonic(linear_t, n_harmonics=3)[0]

            error_field = 'Error in ar'
            autoregressive(harmonic_t, per=2)
            
            print('Everything working fine for {0}'.format(samp_file))
        except:
            print('{0}. Moving forward'.format(error_field))
        
    print ('003 and 006 are expected to fail as only 3 data points are available')
    return

if __name__ == '__main__':
    print('Running test')    
    test()
