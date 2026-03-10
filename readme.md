1. so our goal is to analyze the input and output relationship

input parameters: input_solid.csv (X)
(X1: Hemodynamic parameters)
(X2: Morphology parameters)

output Von mises stress: amp, peak at ./output_VMS.csv (Y1)

output FFR : ./output_FFR.csv (Y2)



1. train surrogate model (GRP or PCE both on a separte python script)

2. test surrogate model (with the 20% of the data sets)

3. get Soblov indices from X -> Y1 and X -> Y2

4. here's my Questions. 

Q1. what if we would like to consider abou the (X, Y2) -> Y1??
(I mean regard FFR as input, is it adequate??)

Q2. I would like to treat combination of X  as input which would be more affective to the Y1.
(so goal is to find the high affective combination of X)
(note in the X)

Q3. compare the effect of the HEmoddynamic vs Morpholgoy combinatio or the strongest one whatever it takes.

Q4. what else can we do with this data set?