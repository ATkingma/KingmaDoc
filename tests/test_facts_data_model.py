"""Tests for the data model KingmaDoc reads from ORM code (`kingmadoc explain facts`)."""

from kingmadoc.facts.data_model import Entity, Field, Relation, data_model
from kingmadoc.facts.projects import project_references

EF_CONTEXT = """\
public class ShopDbContext(DbContextOptions<ShopDbContext> options) : DbContext(options)
{
    public DbSet<OrderEntity> Orders => Set<OrderEntity>();
    public DbSet<CustomerEntity> Customers { get; set; }
}
"""
EF_ORDER = """\
public class OrderEntity
{
    public int Id { get; set; }
    public required string Title { get; set; }
    public DateTimeOffset? PlacedAt { get; init; }
    public CustomerEntity Customer { get; set; } = null!;
    public int CustomerId { get; set; }
    private string Secret { get; set; }
}
"""
EF_CUSTOMER = """\
public class CustomerEntity
{
    public int Id { get; set; }
    public ICollection<OrderEntity> Orders { get; set; } = [];
}
public class NotAnEntity { public int X { get; set; } }
"""


def _names(entities: tuple[Entity, ...]) -> list[str]:
    return [e.name for e in entities]


def test_ef_core_entities_come_from_dbsets() -> None:
    """DbSet<T> names the entities; public properties are fields, entity types relations."""
    model = data_model({
        "Data/ShopDbContext.cs": EF_CONTEXT,
        "Data/OrderEntity.cs": EF_ORDER,
        "Data/CustomerEntity.cs": EF_CUSTOMER,
    })

    assert _names(model) == ["CustomerEntity", "OrderEntity"]
    order = model[1]
    assert order.orm == "EF Core" and order.source == "Data/OrderEntity.cs"
    assert order.fields == (
        Field("Id", "int"), Field("Title", "string"), Field("PlacedAt", "DateTimeOffset?"),
        Field("CustomerId", "int"),
    )
    assert order.relations == (Relation("Customer", "CustomerEntity", "one"),)
    assert model[0].relations == (Relation("Orders", "OrderEntity", "many"),)


def test_ef_core_migrations_are_ignored() -> None:
    """Generated migration snapshots repeat the model; they are not a second definition."""
    model = data_model({
        "Data/ShopDbContext.cs": EF_CONTEXT,
        "Data/OrderEntity.cs": EF_ORDER,
        "Migrations/ShopDbContextModelSnapshot.cs": EF_CONTEXT + "class OrderEntity { }",
    })

    assert [e.source for e in model] == ["Data/OrderEntity.cs"]


def test_prisma_models() -> None:
    """Prisma: scalar fields, and fields typed by another model are relations."""
    schema = """\
model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  posts Post[]
}

model Post {
  id       Int   @id
  author   User  @relation(fields: [authorId], references: [id])
  authorId Int
}

enum Role { USER ADMIN }
"""
    model = data_model({"prisma/schema.prisma": schema})

    assert _names(model) == ["Post", "User"]
    post, user = model
    assert post.fields == (Field("id", "Int"), Field("authorId", "Int"))
    assert post.relations == (Relation("author", "User", "one"),)
    assert user.relations == (Relation("posts", "Post", "many"),)


def test_django_models() -> None:
    """Django: models.Model subclasses; ForeignKey/OneToOne are one, ManyToMany is many."""
    source = """\
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    tags = models.ManyToManyField("Tag")

    def __str__(self):
        return self.title
"""
    model = data_model({"shop/models.py": source})

    assert _names(model) == ["Author", "Book"]
    book = model[1]
    assert book.orm == "Django"
    assert book.fields == (Field("title", "CharField"),)
    assert book.relations == (Relation("author", "Author", "one"), Relation("tags", "Tag", "many"))


def test_sqlalchemy_models() -> None:
    """SQLAlchemy: classes with __tablename__, Column/mapped_column fields, relationship().

    Without a Mapped[...] annotation the side of a relationship is unknown.
    """
    source = """\
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(String(50))
    addresses: Mapped[list["Address"]] = relationship(back_populates="user")

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    user = relationship("User", back_populates="addresses")
"""
    model = data_model({"app/db.py": source})

    assert _names(model) == ["Address", "User"]
    address, user = model
    assert user.orm == "SQLAlchemy"
    assert user.fields == (Field("id", "int"), Field("name", "String"))
    assert user.relations == (Relation("addresses", "Address", "many"),)
    assert address.relations == (Relation("user", "User", "unknown"),)


def test_typeorm_entities() -> None:
    """TypeORM: @Entity classes, @Column fields, relation decorators."""
    source = """\
@Entity()
export class Photo {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @ManyToOne(() => User, (user) => user.photos)
  user: User;

  @OneToMany(() => Tag, (tag) => tag.photo)
  tags: Tag[];
}
"""
    model = data_model({"src/photo.entity.ts": source})

    assert _names(model) == ["Photo"]
    photo = model[0]
    assert photo.orm == "TypeORM"
    assert photo.fields == (Field("id", "number"), Field("name", "string"))
    assert photo.relations == (Relation("user", "User", "one"), Relation("tags", "Tag", "many"))


def test_no_orm_no_entities() -> None:
    """Plain classes are not entities."""
    assert data_model({"a.py": "class A:\n    x = 1\n", "b.cs": EF_ORDER}) == ()


def test_csproj_project_references() -> None:
    """ProjectReference items give the dependencies between .NET projects."""
    manifests = {
        "Api/Api.csproj": '<ItemGroup>\n  <ProjectReference Include="..\\Logic\\Logic.csproj" />\n'
        '  <ProjectReference Include="../Data/Data.csproj"/>\n</ItemGroup>',
        "Logic/Logic.csproj": '<ProjectReference Include="..\\Common\\Common.csproj" />',
        "Common/Common.csproj": "<Project />",
    }

    assert project_references(manifests) == (
        ("Api", "Data"), ("Api", "Logic"), ("Logic", "Common"),
    )
