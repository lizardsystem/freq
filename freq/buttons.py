class LenghtOne(object):

    def __len__(self):
        return 1


class Spinner(LenghtOne):

    def __init__(self, number=0, heading='', title='', step=1, precision=0,
                 min_=0):
        self.heading = heading
        self.title = title
        self.step = step
        self.precision = precision
        self.min = min_
        self.id = 'spinner_' + str(number)


class DropDown(LenghtOne):

    def __init__(self, id_=0, selected=0, heading='', title='', options=None):
        if not options:
            self.options = []
        self.heading = heading
        self.title = title
        self.selected_id = 'dropdown_selected_' + str(selected)
        self.id = id_
