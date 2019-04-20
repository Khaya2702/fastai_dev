/*
THIS FILE WAS AUTOGENERATED! DO NOT EDIT!
file to edit: /home/ubuntu/git/fastai_docs/dev_swift/01_matmul.ipynb/lastPathComponent

*/
        
import Path
import TensorFlow

public extension Tensor where Scalar: TensorFlowFloatingPoint {
    @differentiable func squeeze(_ at: Int )->Tensor { return squeezingShape(at:at) }
    @differentiable func unsqueeze(_ at: Int)->Tensor { return expandingShape(at:at) }
}
