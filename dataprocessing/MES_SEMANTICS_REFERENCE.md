# MES Relationship Semantics - Edge Direction Reference

## Summary of Fixes Applied

**Issue Found**: Comments for `IsSupplementedBy` and `isPartOf` incorrectly stated edge direction as A→B when they should be B→A.

**Fixes Applied**:
1. Corrected comments in OBJECT_TO_SUBJECT to all show B→A edges
2. Removed `IsDocumentedBy` from SUBJECT_TO_OBJECT set (it's handled as special case)
3. Added clarifying comment about IsDocumentedBy special case

## Edge Direction Rules

### For Credit Transfer Graphs:
**An edge A→B means**: "A cites/uses/references B, therefore credit flows from A to B"

### Relationship Categories:

#### OBJECT_TO_SUBJECT (edges from B to A)
When the relation is "A [semantic] B", create edge B→A (from object to subject):

| Semantic | Example | Meaning | Edge Direction |
|----------|---------|---------|----------------|
| **IsReferencedBy** | paper A IsReferencedBy paper B | B references A | B→A ✅ |
| **IsSupplementedBy** | dataset A IsSupplementedBy paper B | B supplements A | B→A ✅ |
| **isPartOf** | dataset A isPartOf paper B | A is part of B | B→A ✅ |
| **isCitedBy** | dataset A isCitedBy paper B | B cites A | B→A ✅ |

**Credit Flow Logic**:
- B→A means B gives credit to A
- IsReferencedBy: B references A, so B credits A ✓
- IsSupplementedBy: B supplements A (B is supplementary to A), so B credits the main work A ✓  
- isPartOf: A is part of B, so the whole (B) credits the part (A) ✓
- isCitedBy: B cites A, so B credits A ✓

#### SUBJECT_TO_OBJECT (edges from A to B)
When the relation is "A [semantic] B", create edge A→B (from subject to object):

| Semantic | Example | Meaning | Edge Direction |
|----------|---------|---------|----------------|
| **references** | paper A references paper B | A cites B | A→B ✅ |
| **cites** | paper A cites dataset B | A cites B | A→B ✅ |
| **documents** | paper A documents dataset B | A describes B | A→B ✅ |
| **IsSupplementTo** | paper A IsSupplementTo dataset B | A supplements B | A→B ✅ |

**Credit Flow Logic**:
- A→B means A gives credit to B
- All of these semantics mean A uses/references B, so A credits B ✓

#### SPECIAL CASES
Handled separately with explicit logic:

| Semantic | Example | Meaning | Edge Direction |
|----------|---------|---------|----------------|
| **IsDocumentedBy** | dataset A IsDocumentedBy paper B | B documents A | B→A ✅ |

**Credit Flow Logic**:
- B→A means B gives credit to A
- B documents A, so the documentation (B) credits the documented entity (A) ✓

## Implementation

```python
# In _parse_relations() method:
if semantic in self.OBJECT_TO_SUBJECT:
    # Edge from object to subject (B → A)
    self.edges.add((obj_internal, subj_internal))
    
elif semantic in self.SUBJECT_TO_OBJECT:
    # Edge from subject to object (A → B)
    self.edges.add((subj_internal, obj_internal))
    
elif semantic == 'IsDocumentedBy':
    # Special case: reverse direction (B → A)
    self.edges.add((obj_internal, subj_internal))
```

## Verification

All edge directions have been verified to be correct for credit transfer:
- ✅ OBJECT_TO_SUBJECT: All create B→A edges (object to subject)
- ✅ SUBJECT_TO_OBJECT: All create A→B edges (subject to object)
- ✅ IsDocumentedBy: Creates B→A edge (special case, correctly implemented)

## Credit Flow Interpretation

In a credit transfer graph:
- **Edge X→Y** means: "X cites/uses/depends on Y, therefore credit flows from X to Y"
- The citing/using entity (X) transfers credit to the cited/used entity (Y)
- This models how research builds on prior work

## Examples

1. **Paper A references Paper B**
   - Relation: "A references B"
   - Edge: A→B
   - Credit flows: Paper A gives credit to Paper B ✓

2. **Paper A IsReferencedBy Paper B**
   - Relation: "A IsReferencedBy B" (means B references A)
   - Edge: B→A
   - Credit flows: Paper B gives credit to Paper A ✓

3. **Dataset A IsSupplementedBy Paper B**
   - Relation: "A IsSupplementedBy B" (B is supplementary material for A)
   - Edge: B→A
   - Credit flows: The supplement (B) gives credit to the main work (A) ✓

4. **Dataset A isPartOf Paper B**
   - Relation: "A isPartOf B" (A is contained in B)
   - Edge: B→A
   - Credit flows: The whole (B) gives credit to its part (A) ✓

All semantics are now correctly documented and implemented!

