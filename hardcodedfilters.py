
class TimeExpressionConstant:
    """Includes some readily-defined groups"""
    finnish_weekdays = [ 'maanantai',
                        'tiistai',
                        'keskiviikko',
                        'torstai',
                        'perjantai',
                        'lauantai',
                        'sunnuntai']

def checkhardcodedrules(self):
    """Go through some rules not found the rules database"""

    if FinnishWDEss(self):
        return 'Applied the Finnish WD + ESS rule ({}....{})'.format(self.head.token,self.dependent.token)
    else:
        return ''


def FinnishWDEss(nontempo):
    """Finnish weekdays in essive will automatically be accepted. Check out.."""
    input('mm')
    if nontempo.dependent.lemma in TimeExpressionConstant.finnish_weekdays and 'CASE_ess' in nontempo.dependent.feat:
        nontempo.rejected = 'n'
        nontempo.evalueatesel()
        return True
    else:
        return False
