import torch
import torch.nn as nn
from torch.nn import Conv2d

def clip_weights_from_pretrain_of_coco_to_cityscapes(f, out_file):
	""""""
	# COCO categories for pretty print
	COCO_CATEGORIES = [
	    "__background__",
	    "person",
	    "bicycle",
	    "car",
	    "motorcycle",
	    "airplane",
	    "bus",
	    "train",
	    "truck",
	    "boat",
	    "traffic light",
	    "fire hydrant",
	    "stop sign",
	    "parking meter",
	    "bench",
	    "bird",
	    "cat",
	    "dog",
	    "horse",
	    "sheep",
	    "cow",
	    "elephant",
	    "bear",
	    "zebra",
	    "giraffe",
	    "backpack",
	    "umbrella",
	    "handbag",
	    "tie",
	    "suitcase",
	    "frisbee",
	    "skis",
	    "snowboard",
	    "sports ball",
	    "kite",
	    "baseball bat",
	    "baseball glove",
	    "skateboard",
	    "surfboard",
	    "tennis racket",
	    "bottle",
	    "wine glass",
	    "cup",
	    "fork",
	    "knife",
	    "spoon",
	    "bowl",
	    "banana",
	    "apple",
	    "sandwich",
	    "orange",
	    "broccoli",
	    "carrot",
	    "hot dog",
	    "pizza",
	    "donut",
	    "cake",
	    "chair",
	    "couch",
	    "potted plant",
	    "bed",
	    "dining table",
	    "toilet",
	    "tv",
	    "laptop",
	    "mouse",
	    "remote",
	    "keyboard",
	    "cell phone",
	    "microwave",
	    "oven",
	    "toaster",
	    "sink",
	    "refrigerator",
	    "book",
	    "clock",
	    "vase",
	    "scissors",
	    "teddy bear",
	    "hair drier",
	    "toothbrush",
	]
	# Cityscapes of fine categories for pretty print
	CITYSCAPES_FINE_CATEGORIES = [
	    "__background__",
	    "person",
	    "rider",
	    "car",
	    "truck",
	    "bus",
        "caravan",
        "trailer",
	    "train",
	    "motorcycle",
	    "bicycle",
	]
	coco_cats = COCO_CATEGORIES
	cityscapes_cats = CITYSCAPES_FINE_CATEGORIES
	coco_cats_to_inds = dict(zip(coco_cats, range(len(coco_cats))))
	cityscapes_cats_to_inds = dict(
		zip(cityscapes_cats, range(len(cityscapes_cats)))
	)

	checkpoint = torch.load(f)
	m = checkpoint['model']

	weight_names = {
		"cls_score": "module.roi_heads.box.predictor.cls_score.weight", 
		"bbox_pred": "module.roi_heads.box.predictor.bbox_pred.weight", 
		"mask_fcn_logits": "module.roi_heads.mask.predictor.mask_fcn_logits.weight", 
	}
	bias_names = {
		"cls_score": "module.roi_heads.box.predictor.cls_score.bias",
		"bbox_pred": "module.roi_heads.box.predictor.bbox_pred.bias", 
		"mask_fcn_logits": "module.roi_heads.mask.predictor.mask_fcn_logits.bias",
	}
	
	representation_size = m[weight_names["cls_score"]].size(1)
	cls_score = nn.Linear(representation_size, len(cityscapes_cats))
	nn.init.normal_(cls_score.weight, std=0.01)
	nn.init.constant_(cls_score.bias, 0)

	representation_size = m[weight_names["bbox_pred"]].size(1)
	class_agnostic = m[weight_names["bbox_pred"]].size(0) != len(coco_cats) * 4
	num_bbox_reg_classes = 2 if class_agnostic else len(cityscapes_cats)
	bbox_pred = nn.Linear(representation_size, num_bbox_reg_classes * 4)
	nn.init.normal_(bbox_pred.weight, std=0.001)
	nn.init.constant_(bbox_pred.bias, 0)

	dim_reduced = m[weight_names["mask_fcn_logits"]].size(1)
	mask_fcn_logits = Conv2d(dim_reduced, len(cityscapes_cats), 1, 1, 0)
	nn.init.constant_(mask_fcn_logits.bias, 0)
	nn.init.kaiming_normal_(
		mask_fcn_logits.weight, mode="fan_out", nonlinearity="relu"
	)
	
	def _copy_weight(src_weight, dst_weight):
		for ix, cat in enumerate(cityscapes_cats):
			if cat not in coco_cats:
				continue
			jx = coco_cats_to_inds[cat]
			dst_weight[ix] = src_weight[jx]
		return dst_weight

	def _copy_bias(src_bias, dst_bias, class_agnostic=False):
		if class_agnostic:
			return dst_bias
		return _copy_weight(src_bias, dst_bias)

	m[weight_names["cls_score"]] = _copy_weight(
		m[weight_names["cls_score"]], cls_score.weight
	)
	m[weight_names["bbox_pred"]] = _copy_weight(
		m[weight_names["bbox_pred"]], bbox_pred.weight
	)
	m[weight_names["mask_fcn_logits"]] = _copy_weight(
		m[weight_names["mask_fcn_logits"]], mask_fcn_logits.weight
	)

	m[bias_names["cls_score"]] = _copy_bias(
		m[bias_names["cls_score"]], cls_score.bias
	)
	m[bias_names["bbox_pred"]] = _copy_bias(
		m[bias_names["bbox_pred"]], bbox_pred.bias, class_agnostic
	)
	m[bias_names["mask_fcn_logits"]] = _copy_bias(
		m[bias_names["mask_fcn_logits"]], mask_fcn_logits.bias
	)

	print("f: {}\nout_file: {}".format(f, out_file))
	torch.save(m, out_file)

if __name__ == "__main__":
    coco = "e2e_mask_rcnn_R_50_FPN_1x.pth"
    out = "e2e_mask_rcnn_R_50_FPN_1x_cityscapes.pth"
    clip_weights_from_pretrain_of_coco_to_cityscapes(coco, out)