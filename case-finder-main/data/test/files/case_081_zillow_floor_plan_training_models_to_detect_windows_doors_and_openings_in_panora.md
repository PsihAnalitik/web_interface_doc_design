# Zillow Floor Plan: Training Models to Detect Windows, Doors and Openings in Panoramas

- **Sample ID**: case_081
- **Source URL**: https://www.zillow.com/tech/training-models-to-detect-windows-doors-in-panos/
- **Content type**: article

---

Floor plans give home shoppers a quick yet effective grasp of the home layout like no other media is able to offer. They not only show the scale of each space, but also the key relationships between rooms and the flow of a home.
At Zillow, we recently embarked on a journey to generate floor plans (Fig. 1) from a series of 360 degree panoramas densely captured in a home. Having our floor plan generator process automatically detect wall features such as windows, doors, and openings (WDOs) from the panoramas was an essential step. Home shoppers use WDOs to orient themselves when navigating through the home. Additionally, during the generation of floor plans, WDOs serve as key intersection points for piecing together a room shape from images taken in different locations of a home.
Fig 1. Examples of Zillow generated floor plans.
The task this blog focuses on is a small step in floor plan generation from 360-degree panoramas. Given an indoor 360 pano, can we detect and localize all WDOs using bounding boxes? A precise statement on the input/output requirement of a task is the key to clearly defining a project.
The Input: a panorama of indoor environments that is leveled. By requiring a leveled panorama, we can safely assume that the north pole aligns with the y-axis of the equirectangular projection of the panoramic image.
The Output: tight bounding boxes on the left/right, but not on the top/bottom. The top-bottom boundaries are relaxed due to horizontal distortions in the equirectangular projection. We will provide more explanations in the data/annotation collection section.
The major components of our wall feature detection development pipeline are shown in Fig. 2. It follows the universal workflow of a machine learning project with some adaptations to our business problem. Unlike research projects that start with a public dataset, we examined the existing datasets on their definitions and decided to redefine the wall feature classes including the appearance and manner of annotation that can help us draw WDOs on floor plans later on.
With the new annotations defined, it was important that our annotators produce consistent annotations of good quality. We accumulated some experience in the data labeling stage. One other highlight was our choice for modeling. There are two different routes for training an object detection model and we will explain why we went with the option of training directly on the 360 panorama. Finally, we show some qualitative and quantitative results and compare model performance against human performance. Model deployment and integration of model predictions to our pipeline will be discussed in detail in a follow-up blog.
Fig 2. Major components of the current object detection pipeline. The components in the dotted rectangle will be discussed in an upcoming blog that focuses on model deployment and integration.
Having defined the task and the input and output, the next phase was data gathering and annotation, as we modeled the problem using a supervised learning approach.
In this phase, the main question we tried to answer was which classes did we want to collect and what were the class definitions?
Let’s begin by explaining the importance of class definition with a concrete example. During our research on existing datasets, two well-known public datasets ADE20K and Open Images Dataset caught our eyes since they both have the class of doors. As seen in Fig. 3., the annotations both dataset provided are on the doors (data not shown for ADE20K). However, would the same definition address our needs? The answer to this question always lie in the final business need - to show the position of WDOs on a 2D floor plan. It was clear that the position of doors should not change no matter if the door is open or closed in the panorama. What really mattered was the space underneath the door, that functionally separates two rooms, not the location of doors or the frames that are visually in an image. From this example, we learned that there is no universal definition for an object and this unique definition tailored to our problem is the key for building a custom model to address our concrete business needs.
Fig 3. Example annotation of doors in open image dataset. Door annotation is highlighted using yellow boxes. Door annotations we look for are indicated using blue boxes. Image used in figs. 3a and 3b created by Léo Ruas, subject to CC BY 2.0 license (link). Image only shown for illustrative purposes and has not been used for training or evaluation.
Another distinction from the regular object detection task is that our input data is a 360 panorama. Unlike a perspective camera that samples a limited field of view, a 360-degree camera captures the omnidirectional view of a scene. A common way of visualizing the 360 panorama is to project it onto a single planar image via equirectangular projection . This projection will introduce a varying amount of distortions across the viewing sphere (Fig. 4a) and thus pose challenges on the definition of bounding boxes. One immediate challenge we saw was that a four-point polygon bounding box is not able to capture the full object as the object is curved. We wondered, would a bounding box covering only a portion of a door impose a negative impact on how they show up in a floor plan? Not really! The requirement of leveled equirectangular projection preserves all vertical lines and thereby the left and right boundaries. Once the left and right boundaries of a door are precisely captured and then intersected with the floor plane, the location of a door on the floor plan is determined.
Deviating from the conventional definitions, here are the definitions of our proposed three classes:
It should be noted that we do not differentiate between the interior and exterior doors because both types need to be identified on a floor plan. Closet doors are also included as interior doors.
Fig. 4 Illustration on the distortion effects created due to projection and how are doors, openings, and windows defined and labeled on 360 panoramas.
One effective strategy we followed before we began labelling data, was to go through many example images and reach an agreement on how to label them. We were surprised by how much debate we had amongst ourselves on such a simple task. What came out of these discussions are concrete instructions on how to label each class with positive and negative examples for our in-house annotators. These instructions are critical for getting good annotations.
Even with that effort, it was impossible to capture all corner cases. Some examples are illustrated in Fig. 5. This ambiguity existed in almost all datasets and there were always multiple ways of labelling the same object. The key takeaway here was the need for consistency in annotation. For example, if we decided to label shower doors, then all shower doors need to be labelled throughout the dataset. As a result, we set up daily review sessions in the first week, where annotators presented cases they had doubts about, and we discussed and reached a consensus as a team on how to label these cases. Later on if annotators had questions, they would post them in the slack channel and we can quickly follow up.
Fig. 5 Corner cases for WDO annotations. (a) How do we label occluded doors? (b) Are shower doors counted as doors? (c) How do we handle objects on loop closure? (d) Do we annotate objects in a mirror?
Within two months, we have collected annotations for about 10,000 panoramas. On average, there are 6 bounding boxes in each panorama, including 2.7 doors, 2.3 windows and 1.0 openings. This unique dataset is the core asset of this project.
Fig 6. Two routes for training a model. In route 1, perspective crops with a fixed field of view (FOV), together with the annotated bounding boxes are extracted. Then an object detection model is trained on the perspective images. During inference, the bounding boxes from the crops will need to be fused to output predicted bounding boxes for the panorama. In route 2, we could directly train an object detection model on panoramas, with or without modifications on convolutions/pooling operations.
Thanks to the recent advancement in deep learning models as part of the mature machine learning field, object detection models have been turned into basic, readily available models in many of the open source deep learning frameworks and model zoo collections. However, most of the existing models such as TensorFlow object detection API and Detectron library by Facebook , are trained on perspective images. Overall we saw two routes to train the model. In the first route, we would first convert the panorama into multiple perspective crops and then perform detections on the crops followed by fusing the detections on each crop (Route 1 in Fig. 6).
Alternatively, we could choose route 2 and apply the Convolutional Neural Network (CNN) model directly on panoramas (Route 2 in Fig. 6). On that path there are also 2 sub-options.
(a) Apply off-the-shelf CNNs and “close your eyes” by treating the equirectangular projections as “flat” images.
(b) Adapt the convolutional and pooling operations to the spherical space. Spherical convolutions have been a hot research topic. Several research papers have pointed out that features learned from CNNs on flat images are different from features from 360° images and researchers have made various explorations on modifying convolutions to adapt to spherical space .
Faced with these two routes, which one should we choose?
We chose the simplest route, 2a.. The main drive for route 1 lies in removing distortions caused by the equirectangular projection and we have good knowledge that the object detection model would work well on flat images. However, the additional extraction and fusion steps would have added an extra amount of pre(post) processing to the pipeline, as well as inference time since each panorama requires inference on multiple perspective images.
As to the sub-options in route 2, we believed the networks should be tolerant to the amount of distortions for the following reasons. First, since we required a leveled panorama as input, the horizontal lines stay horizontal in equirectangular projection. On the other hand, most objects of interest exist in the less deformed regions of the panoramas and the texture of WDOs were easily identifiable by human eyes, and likely to be picked up by convolutional filters. Finally, it is worth mentioning that we had collected a good size of annotations on the 360 panoramas. This dataset allowed us to train and evaluate directly on panorama without modifications on the object detection model.
We trained a Single Shot Multibox Detector (SSD) model and Faster R-CNN model on the panorama directly. The results look promising (Fig. 7). We report the results in the next section.
Fig. 7. Qualitative results for WDO detection on 360 panorama using Faster R-CNN. Green, red and blue boxes represent windows, doors and openings, respectively. Values in the boxes indicate the confidence score of the class.
Although in this blog model evaluation appears after data collection and model training, agreeing on the business/target metric usually happens much earlier in the life-time of ML projects. While it is natural for metrics to evolve and change over time, determining evaluation metrics during the project planning stage is considered a best practice.
Localizing WDOs is a task that humans can do well easily. For those tasks, human-level performance can give us a very good estimate on the targeted error rate.
Then how do we measure human performance of this task? First we selected over 300 panoramas for all annotators to label. We treated one judge’s annotation as ground truth and measured the precision/recall for other judges to understand annotation consistency and accuracy. Guess what? Humans did not get a perfect score on this task (Fig. 8).
We calculated the average precision of each class (Table 1). Overall, doors are most consistently identified while openings was the least consistent class. Explorations on the inconsistent annotations gave us potential causes of the human-to-human disagreement (Fig. 9).
In the first example, we saw different views on what qualified as an opening among annotators. The second example showed human error during annotation. A door was mislabeled as an opening by one annotator. The last discrepancy was subtle. When three windows were next to each other, some annotators labeled them as one window while others labeled these windows separately. These examples demonstrated that despite daily rubrics, it remains a challenge for humans to follow the labeling guidelines and produce 100% consistent annotations.
Luckily, many evaluation metrics already exist for object detection tasks. We chose to use a precision-recall curve to understand the overall performance of a model at different confidence thresholds and average precision (AP) defined in the PASCAL VOC 2010 challenge as a single-number evaluation metric.
Fig. 8 Human performance on wall feature object detection. We asked three judges A, B and C to annotate the same set of panoramas and treat one judge’s annotation as ground truth and measure the precision/recall of the rest.
Fig.9 Examples of inconsistent annotations on the same panorama. A,B,C represent annotations from 3 different annotators.
We chose two models to experiment with, SSD and Faster R-CNN. At the time of writing this blog post, these two models are good representatives for one-stage and two-stage object detection models. Among all annotated panoramas, we used 70% for training, 15% for validation and 15% for testing. The precision-recall curve gives an overview of how the model does at different confidence thresholds. For a perfect model, the area under the curve would be one. As you can see above, even with human performance, it was well below one. Similar to human performance, the models performed best with door detection, followed by windows and openings (Fig. 10).
Table 1. Average precision for inter-annotator performance and model performance for each class
We used the average precision as a single metric to compare models (Table 1). Both models performed well on 360 panoramas. Specifically, the overall performance of Faster R-CNN was better than that of SSD. This is expected as the one stage model is usually lower in accuracy in exchange for faster inference time and simpler architecture. Another interesting point from the table was that the performance of Faster R-CNN on doors and windows was very close to human performance. As to openings, the gap between the model and human performance was wider, presumably because of subjective judgement on what qualifies as an opening and the model had a difficult time finding a consistent pattern.
Fig 10. Precision-recall curve of Faster R-CNN model at IoU =0.5
In this blog post, we have walked you through the first part of the wall feature detection project. Here are some key takeaways.
In the next blog, we will discuss in depth how we designed and implemented the infrastructure that would deploy and serve our models.
We would like to thank the applied science team in RMX for all the useful discussion and support for this project.
Related Articles
Subscribe to receive daily emails for the latest Zillow news and announcements, product updates and more.
---

## Extracted images (14)

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_001.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-1-8e80f7.png]
[IMAGE_DESCRIPTION: PATIO 1544" x79" LIVING ROOM 244" x 16:2" BEDROOM 154" x 183" DINING ROOM 1941" x 103" KITCHEN LAUNDRY tent" x 198" ROOM BATHROOM 6:3" x6'5" 126" x 11'5" D > z 5 zB = BATHROOM 53" x3'6" CLOSET 192" x57" FAMILY ROOM 164" x 190" —_ A Entry GARAGE 192" x 193" (a) BATH 3'3" x 5'6" BATHROOM 5'8" x 9'6" CLOSET BEDROOM 12'2" x 13'8" BEDROOM 172" x 13'8" CLOSET BATHROOM 5'8" x 3'4" BATHROOM 10'6" x 511" BEDROOM 18°11" x 18'8" BEDROOM 12'2" x 17'2" LOFT 21'6" x 37'2"]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_002.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-2-6f6d15.png]
[IMAGE_DESCRIPTION: v]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_003.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-3-3789de.png]
[IMAGE_DESCRIPTION: (a) Annotated doors from (b) Annotations on doors Open Image dataset we need]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_004.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-4-860b3d.png]
[IMAGE_DESCRIPTION: - - sia as = le eat) 1 ih (a) Distortion as a result of equirectangular projection (b) Opening (c) Door (d) Window]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_005.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-5-0a20db.png]
[IMAGE_DESCRIPTION: rl a (a) Occluded door? (b) Shower door? —_ (c) Door on a loop closure? (d) Door in a mirror?]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_006.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-6-e27e39.png]
[IMAGE_DESCRIPTION: Divide and conquer Detect wall features on crops 7] —} Fuse bounding boxes from crops al Extract perspective crops Route 2: Directly perform object detection on panorama]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_007.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-7-a5d62d.png]
[IMAGE_DESCRIPTION: door: 1.00 door: 1.00 door: 1.00 door: 1.00 door: 1.00 door: 1.00 door: 1.00]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_008.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-8-0b02fe.png]
[IMAGE_DESCRIPTION: Precision oO je) ron for) Oo aa Oo ho “0.0 window apne CRC 0.2 0.4 0.6 0.8 1.0 Recall 1.0 Precision oO ron Oo aa Oo ho 0.0 0.2 door 0.4 0.6 Recall opening ée 1.0 -B Cy BEA O8 Precision ro) ron tw > Oo aa Oo ho 0.8 1.0 0.0 0.2 0.4 0.6 0.8 1.0 Recall]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_009.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-9-c32e63.png]
[IMAGE_DESCRIPTION: 1. Subjective opinion on opening 2. Missing annotation 3. One window vs three windows]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_010.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-10-1c82f5.png]
[IMAGE_DESCRIPTION: Window 0.772 0.764 0.683 Door 0.881 0.855 0.774 Opening 0.720 0.577 0.523]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_011.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/WDO_Figure-11-b26608.png]
[IMAGE_DESCRIPTION: Precision precision-recall curve @loU=0.5 1.0 0.8 0.6 0.4 02 o— window — door —= opening 0.0 0.0 0.2 0.4 0.6 0.8 1.0 Recall]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_012.jpg]
[IMAGE_ALT: multicolored houses with flowers]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/2026/06/Header_May-Market-Report_1600x900_1-1280x720.jpg]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_013.jpg]
[IMAGE_ALT: real estate agent outside of house with a for sale sign]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/2026/06/Header_Direct-Broker_1600x900_1-1280x720.jpg]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_081/img_014.svg]
[IMAGE_ALT: illustration of mailbox]
[IMAGE_SOURCE_URL: https://delivery.digitallibrary.zillowgroup.com/public/mailbox-light_svg_Original.svg]
[IMAGE_DESCRIPTION: SKIPPED_SVG]
