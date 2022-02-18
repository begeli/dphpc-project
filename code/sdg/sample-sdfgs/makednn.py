import torch
import torch.nn.functional as F
import daceml.onnx as donnx
from daceml.pytorch import DaceModule, dace_module


donnx.default_implementation = 'pure'

# Input and size definition
B, H, P, SM, SN = 2, 16, 64, 512, 512
N = P * H
Q, K, V = [torch.randn([SN, B, N]), torch.randn([SM, B, N]), torch.randn([SM, B, N])]

@dace_module
class Feedforward(torch.nn.Module):
    def __init__(self, input_size, hidden_size):
        #super(Feedforward, self).__init__()
        super().__init__()
        self.input_size = input_size
        self.hidden_size  = hidden_size
        self.fc1 = torch.nn.Linear(self.input_size, self.hidden_size)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(self.hidden_size, 1)
        self.sigmoid = torch.nn.Sigmoid()        
        
    def forward(self, x):
        hidden = self.fc1(x)
        relu = self.relu(hidden)
        output = self.fc2(relu)
        output = self.sigmoid(output)
        return output

@dace_module
class MLP(torch.nn.Module):
    def __init__(self, input_size, num_classes, fc1=17, fc2=19):
        super().__init__()
        self.fc1 = torch.nn.Linear(input_size, fc1)
        self.fc2 = torch.nn.Linear(fc1, fc2)
        self.fc3 = torch.nn.Linear(fc2, num_classes)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        x = F.log_softmax(x, dim=1)
        return x

# DaCe module used as a decorator
@dace_module
class ConvModel(torch.nn.Module):
    def __init__(self, kernel_size):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 4, kernel_size)
        self.conv2 = torch.nn.Conv2d(4, 4, kernel_size)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        return F.relu(self.conv2(x))

model = MLP(1000, 300)
model(torch.rand(8, 1000))
model.sdfg.save('MLP.sdfg')



model = Feedforward(1000, 300)
model(torch.rand(8, 1000))
model.sdfg.save('ff.sdfg')


dace_model = ConvModel(3)
outputs_dec = dace_model(torch.rand(1, 1, 8, 8))