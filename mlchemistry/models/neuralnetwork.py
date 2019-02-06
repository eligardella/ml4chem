import time
import datetime
import torch
import torch.nn as nn

from mlchemistry.backends.operations import BackendOperations as backend
from mlchemistry.data.visualization import parity

torch.set_printoptions(precision=10)

class NeuralNetwork(nn.Module):
    """Neural Network Regression with Pytorch

    Parameters
    ----------
    hiddenlayers : tuple
        Structure of hidden layers in the neural network.
    epochs : int
        Number of full training cycles.
    convergence : dict
        Instead of using epochs, users can set a convergence criterion.
    device : str
        Calculation can be run in the cpu or gpu.
    lr : float
        Learning rate.
    optimizer : object
        An optimizer class.
    activation : str
        The activation function.
    weight_decay : float
        Weight decay passed to the optimizer. Default is 0.
    regularization : float
        This is the L2 regularization. It is not the same as weight decay.
    """

    def __init__(self, hiddenlayers=(3, 3), epochs=100, convergence=None,
                 device='cpu', lr=0.001, optimizer=None,
                 activation='relu', weight_decay=0., regularization=0.):
        super(NeuralNetwork, self).__init__()
        self.epochs = epochs
        self.device = device.lower()    # This is to assure we are in lowercase
        self.lr = lr
        self.optimizer = optimizer
        self.activation = activation
        self.hiddenlayers = hiddenlayers
        self.weight_decay = weight_decay
        self.regularization = regularization
        self.convergence = convergence

    def forward(self, X):
        """Forward propagation

        This is forward propagation and it returns the atomic energy.

        Parameters
        ----------
        X : list
            List of features.

        Returns
        -------
        image_energy : float
            Energy of an image.
        """

        atomic_energies = []

        for symbol, x in X:
            x = torch.tensor(x, requires_grad=False)
            x = x.unsqueeze(0)
            x = self.linears[symbol](x)

            intercept_name = 'intercept_' + symbol
            slope_name = 'slope_' + symbol

            for name, param in self.named_parameters():
                if intercept_name == name:
                    intercept = param
                elif slope_name == name:
                    slope = param

            atomic_energy = (slope * x) + intercept
            atomic_energies.append(atomic_energy)

        atomic_energies = torch.cat(atomic_energies)

        image_energy = torch.sum(atomic_energies)
        return image_energy

    def train(self, feature_space, targets, data=None):
        """Train the model

        Parameters
        ----------
        feature_space : dict
            Dictionary with hashed feature space.
        targets : list
            The expected values that the model has to learn aka y.
        data : object
            DataSet object created from the handler.
        """
        activation = {'tanh': nn.Tanh, 'relu': nn.ReLU, 'celu': nn.CELU}

        print()
        print('Model Training')
        print('==============')
        print('Number of hidden-layers: {}' .format(len(self.hiddenlayers)))
        print('Structure of Neural Net: {}' .format('(input, ' +
                                                    str(self.hiddenlayers)[1:-1]
                                                    + ', output)'))
        layers = range(len(self.hiddenlayers) + 1)
        unique_element_symbols = data.unique_element_symbols['trainingset']

        symbol_model_pair = []
        self.output_layer_index = {}

        for symbol in unique_element_symbols:
            linears = []

            intercept = (data.max_energy + data.min_energy) / 2.
            intercept = nn.Parameter(torch.tensor(intercept, requires_grad=True))

            slope = (data.max_energy - data.min_energy) / 2.
            slope = nn.Parameter(torch.tensor(slope, requires_grad=True))

            print(intercept, slope)
            intercept_name = 'intercept_' + symbol
            slope_name = 'slope_' + symbol

            self.register_parameter(intercept_name, intercept)
            self.register_parameter(slope_name, slope)

            for index in layers:
                # This is the input layer
                if index == 0:
                    inp_dimension = len(list(feature_space.values())[0][0][-1])
                    out_dimension = self.hiddenlayers[0]
                    _linear = nn.Linear(inp_dimension, out_dimension)
                    linears.append(_linear)
                    linears.append(activation[self.activation]())
                # This is the output layer
                elif index == len(self.hiddenlayers):
                    inp_dimension = self.hiddenlayers[index - 1]
                    out_dimension = 1
                    self.output_layer_index[symbol] = index
                    _linear = nn.Linear(inp_dimension, out_dimension)
                    linears.append(_linear)
                # These are hidden-layers
                else:
                    inp_dimension = self.hiddenlayers[index - 1]
                    out_dimension = self.hiddenlayers[index]
                    _linear = nn.Linear(inp_dimension, out_dimension)
                    linears.append(_linear)
                    linears.append(activation[self.activation]())

            # Stacking up the layers.
            linears = nn.Sequential(*linears)
            symbol_model_pair.append([symbol, linears])

        self.linears = nn.ModuleDict(symbol_model_pair)
        print(self.linears)

        # Iterate over all modules and just intialize those that are a linear
        # layer.
        for m in self.modules():
            if isinstance(m, nn.Linear):
                # nn.init.normal_(m.weight)   # , mean=0, std=0.01)
                nn.init.xavier_uniform_(m.weight)

        old_state_dict = {}
        for key in self.state_dict():
            old_state_dict[key] = self.state_dict()[key].clone()

        targets = torch.tensor(targets, requires_grad=False)

        # Define optimizer
        if self.optimizer is None:
            self.optimizer = torch.optim.Adam(self.parameters(), lr=self.lr,
                                              weight_decay=self.weight_decay)

        print()
        print('{:6s} {:19s} {:8s}'.format('Epoch', 'Time Stamp', 'Loss'))
        print('{:6s} {:19s} {:8s}'.format('------',
                                          '-------------------', '---------'))
        initial_time = time.time()

        _loss = []
        _rmse = []
        epoch = 0
        while True:
            epoch += 1
            outputs = []

            for hash, fs in feature_space.items():

                image_energy = self.forward(fs)
                outputs.append(image_energy)

            outputs = torch.stack(outputs)
            loss, rmse = self.get_loss(outputs, targets, data.atoms_per_image)
            _loss.append(loss)
            _rmse.append(rmse)

            ts = time.time()
            ts = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d '
                                                              '%H:%M:%S')
            print('{:6d} {} {:8e} {:8f}' .format(epoch, ts, loss, rmse))

            if self.convergence is None and epoch == self.epochs:
                break
            elif (self.convergence is not None and
                  rmse < self.convergence['energy']):
                break

        training_time = time.time() - initial_time

        print('Training the model took {}...' .format(training_time))
        print('outputs')
        print(outputs)
        print('targets')
        print(targets)

        new_state_dict = {}
        for key in self.state_dict():
            new_state_dict[key] = self.state_dict()[key].clone()

        for key in old_state_dict:
            if not (old_state_dict[key] == new_state_dict[key]).all():
                print('Diff in {}'.format(key))
            else:
                print('No diff in {}'.format(key))

        print()

        for symbol in unique_element_symbols:
            model = self.linears[symbol]
            print('Optimized parameters for {} symbol' .format(symbol))

            for index, param in enumerate(model.parameters()):
                print('Index {}' .format(index))
                print(param)
                try:
                    print('Gradient', param.grad.sum())
                except AttributeError:
                    print('No gradient?')

                print()
        parity(self.backend.to_numpy(outputs),
               self.backend.to_numpy(targets))
        import matplotlib.pyplot as plt
        plt.plot(list(range(epoch)), _loss, label='loss')
        plt.plot(list(range(epoch)), _rmse, label='rmse/atom')
        plt.legend(loc='upper left')
        plt.show()

    def get_loss(self, outputs, targets, atoms_per_image):
        """Get loss function value

        Parameters
        ----------
        outputs : list
            List or tensor with outputs from the Neural Networks.
        targets : list
            List or tensor with expected values.
        atoms_per_image : list
            List or tensor with number of atom in each image

        Returns
        -------
        loss : float
            Current value of loss function.
        """
        self.optimizer.zero_grad()  # clear previous gradients


        atoms_per_image = torch.tensor(atoms_per_image, requires_grad=False,
                                       dtype=torch.float)
        outputs_atom = torch.div(outputs, atoms_per_image)
        targets_atom = torch.div(targets, atoms_per_image)
        #print(outputs.shape)
        #print(targets.shape)
        #print(outputs_atom.shape)
        #print(targets_atom.shape)
        #print(atoms_per_image.shape)

        rmse = torch.sqrt(torch.mean(torch.pow((outputs - targets), 2)))
        criterion = nn.MSELoss(reduction='sum')
        loss = criterion(outputs_atom, targets_atom) / 2.

        if self.regularization > 0:
            # L2 regularization does not seem to be the same as weight_decay.
            # See: https://arxiv.org/abs/1711.05101
            l2 = 0.

            for name, parameters in self.named_parameters():
                if 'weight' in name:
                    l2 += parameters.norm(2)

            loss = loss + (l2 * self.regularization)

        loss.backward()
        self.optimizer.step()
        return loss, rmse
